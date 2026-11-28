import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import makeWASocket, {
  DisconnectReason,
  downloadMediaMessage,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  proto,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import QRCode from 'qrcode';

const PORT = Number(process.env.RAA_WA_BRIDGE_PORT || 8766);
const AUTH_DIR = process.env.RAA_WA_AUTH_DIR || path.resolve('.raa-workspace', 'whatsapp_auth');
const INBOX_DIR = path.resolve('.raa-workspace', 'inbox', 'whatsapp');

const silentLogger = {
  level: 'silent',
  child() { return this; },
  trace() {},
  debug() {},
  info() {},
  warn() {},
  error() {},
};

let sock = null;
let state = 'disconnected'; // disconnected | connecting | qr_ready | connected | error
let latestQr = '';
let latestQrSvg = '';
let latestPairingCode = '';
let connectedPhone = '';
let connectedName = '';
let lastError = '';
let starting = false;
let loggedOutRemotely = false;
let reconnectTimer = null;
let sendChain = Promise.resolve();
const inboxQueue = [];
const sentByRaaIds = new Set();
const sentMessageStore = new Map();
const phoneDigitsToChatJid = new Map();
const recentEvents = [];

function jidMapPath() {
  return path.join(AUTH_DIR, 'jid_map.json');
}

function loadJidMap() {
  try {
    const file = jidMapPath();
    if (!fs.existsSync(file)) return;
    const obj = JSON.parse(fs.readFileSync(file, 'utf-8'));
    if (obj && typeof obj === 'object') {
      for (const [digits, jid] of Object.entries(obj)) {
        if (digits && jid) phoneDigitsToChatJid.set(digits, String(jid));
      }
    }
  } catch {}
}

function saveJidMap() {
  try {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
    fs.writeFileSync(jidMapPath(), JSON.stringify(Object.fromEntries(phoneDigitsToChatJid)), 'utf-8');
  } catch {}
}

function resolveTargetJid(digits) {
  const mapped = phoneDigitsToChatJid.get(digits);
  if (mapped) return mapped;
  const selfDigits = connectedPhone.replace(/\D/g, '');
  if (selfDigits && digits === selfDigits && sock?.user?.lid) {
    return String(sock.user.lid).replace(/:.*@/, '@');
  }
  return `${digits}@s.whatsapp.net`;
}

function sentStorePath() {
  return path.join(AUTH_DIR, 'sent_store.json');
}

function loadSentStore() {
  try {
    const file = sentStorePath();
    if (!fs.existsSync(file)) return;
    const raw = fs.readFileSync(file, 'utf-8');
    const entries = JSON.parse(raw, (_k, v) => {
      if (v && typeof v === 'object' && v.type === 'Buffer' && Array.isArray(v.data)) {
        return Buffer.from(v.data);
      }
      return v;
    });
    if (Array.isArray(entries)) {
      for (const [id, msg] of entries) {
        if (id && msg) {
          sentByRaaIds.add(id);
          try {
            sentMessageStore.set(id, proto.Message.fromObject(msg));
          } catch {
            sentMessageStore.set(id, msg);
          }
        }
      }
    }
  } catch {}
}

function saveSentStore() {
  try {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
    const entries = Array.from(sentMessageStore.entries()).slice(-200);
    fs.writeFileSync(sentStorePath(), JSON.stringify(entries), 'utf-8');
  } catch {}
}

function enqueueSend(fn) {
  const run = sendChain.then(async () => {
    const res = await fn();
    await new Promise((r) => setTimeout(r, 150));
    return res;
  });
  sendChain = run.catch(() => {});
  return run;
}

function recordDebugEvent(evt) {
  recentEvents.push({ ts: Date.now(), ...evt });
  if (recentEvents.length > 20) recentEvents.shift();
}

function unwrapMessage(raw) {
  let m = raw || {};
  for (let i = 0; i < 5; i++) {
    if (m.ephemeralMessage?.message) m = m.ephemeralMessage.message;
    else if (m.viewOnceMessage?.message) m = m.viewOnceMessage.message;
    else if (m.viewOnceMessageV2?.message) m = m.viewOnceMessageV2.message;
    else if (m.deviceSentMessage?.message) m = m.deviceSentMessage.message;
    else if (m.editedMessage?.message) m = m.editedMessage.message;
    else if (m.documentWithCaptionMessage?.message) m = m.documentWithCaptionMessage.message;
    else break;
  }
  return m;
}

function trackSentMessage(result) {
  const id = result?.key?.id;
  if (!id) return;
  sentByRaaIds.add(id);
  if (result?.message) {
    sentMessageStore.set(id, result.message);
  }
  if (sentByRaaIds.size > 500) {
    const first = sentByRaaIds.values().next().value;
    if (first) {
      sentByRaaIds.delete(first);
      sentMessageStore.delete(first);
    }
  }
  saveSentStore();
}

function isSelfChatJid(remoteJid, msg, authState) {
  const candidates = [remoteJid, msg?.key?.remoteJidAlt].filter(Boolean);
  const selfDigits = connectedPhone.replace(/\D/g, '');
  const selfLid = (sock?.user?.lid || authState?.creds?.me?.lid || '').replace(/@.*/, '').split(':')[0];
  for (const jid of candidates) {
    const jidUser = String(jid).replace(/@.*/, '').split(':')[0];
    if (selfDigits && jidUser === selfDigits) return true;
    if (selfLid && jidUser === selfLid) return true;
  }
  return false;
}

async function startSocket(pairPhone = '') {
  if (starting) return;
  starting = true;
  lastError = '';
  state = 'connecting';
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  try {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
    loadSentStore();
    loadJidMap();
    const { state: authState, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    let version;
    try {
      const latest = await fetchLatestBaileysVersion();
      version = latest.version;
    } catch {
      version = undefined;
    }

    if (sock) {
      const prevSock = sock;
      sock = null;
      try { prevSock.end(undefined); } catch {}
    }

    const currentSock = makeWASocket({
      ...(version ? { version } : {}),
      auth: {
        creds: authState.creds,
        keys: makeCacheableSignalKeyStore(authState.keys, silentLogger),
      },
      logger: silentLogger,
      printQRInTerminal: false,
      browser: ['RAA Studio', 'Chrome', '4.0.0'],
      syncFullHistory: false,
      markOnlineOnConnect: true,
      getMessage: async (key) => {
        const stored = key?.id ? sentMessageStore.get(key.id) : undefined;
        return stored || undefined;
      },
    });
    sock = currentSock;

    currentSock.ev.on('creds.update', () => {
      if (currentSock !== sock) return;
      void saveCreds();
    });

    currentSock.ev.on('messages.upsert', async ({ messages, type }) => {
      if (currentSock !== sock) return;
      if (type !== 'notify') return;
      for (const msg of messages || []) {
        if (!msg) continue;
        const msgId = msg.key?.id || '';
        const remoteJid = msg.key?.remoteJid || '';
        const m = unwrapMessage(msg.message);
        const msgKeys = Object.keys(m);
        if (msg.key?.fromMe) {
          if (sentByRaaIds.has(msgId)) {
            recordDebugEvent({ type, fromMe: true, remoteJid, msgKeys, accepted: false, reason: 'sent_by_raa' });
            continue;
          }
          if (!isSelfChatJid(remoteJid, msg, authState)) {
            recordDebugEvent({ type, fromMe: true, remoteJid, remoteJidAlt: msg.key?.remoteJidAlt || '', msgKeys, accepted: false, reason: 'not_self_chat' });
            continue;
          }
        }
        const altJid = msg.key?.remoteJidAlt || '';
        const pickJid = remoteJid.endsWith('@lid') && altJid ? altJid : remoteJid;
        const senderDigits = pickJid.endsWith('@lid')
          ? connectedPhone.replace(/\D/g, '')
          : pickJid.replace(/@.*/, '').split(':')[0];
        const sender = senderDigits ? `+${senderDigits}` : (connectedPhone || remoteJid);
        if (senderDigits && remoteJid && !remoteJid.endsWith('@g.us')) {
          const cleanRemote = remoteJid.replace(/:.*@/, '@');
          if (phoneDigitsToChatJid.get(senderDigits) !== cleanRemote) {
            phoneDigitsToChatJid.set(senderDigits, cleanRemote);
            saveJidMap();
          }
        }
        const text =
          m.conversation ||
          m.extendedTextMessage?.text ||
          m.documentMessage?.caption ||
          m.imageMessage?.caption ||
          '';
        let attachmentPath = '';
        let attachmentName = '';
        if (m.documentMessage) {
          try {
            fs.mkdirSync(INBOX_DIR, { recursive: true });
            const rawName = String(m.documentMessage.fileName || `wa_${Date.now()}.bin`).replace(/[^a-zA-Z0-9._-]/g, '_');
            const buf = await downloadMediaMessage(msg, 'buffer', {}, { logger: silentLogger, reuploadRequest: sock.updateMediaMessage });
            const outFile = path.join(INBOX_DIR, rawName);
            fs.writeFileSync(outFile, buf);
            attachmentPath = outFile;
            attachmentName = rawName;
          } catch (dlErr) {
            lastError = String(dlErr?.message || dlErr);
          }
        }
        if (text || attachmentPath) {
          recordDebugEvent({ type, fromMe: Boolean(msg.key?.fromMe), remoteJid, sender, textLen: String(text || '').length, accepted: true });
          inboxQueue.push({
            id: msg.key?.id || `wa_in_${Date.now()}`,
            channel: 'whatsapp',
            sender,
            text: String(text || '').trim(),
            attachment_path: attachmentPath,
            attachment_name: attachmentName,
            timestamp: Date.now(),
          });
          if (inboxQueue.length > 100) inboxQueue.shift();
        }
      }
    });

    currentSock.ev.on('connection.update', async (update) => {
      if (currentSock !== sock) return;
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        latestQr = qr;
        try {
          latestQrSvg = await QRCode.toString(qr, {
            type: 'svg',
            width: 220,
            margin: 2,
            color: { dark: '#0A0E17', light: '#FFFFFF' },
          });
        } catch {
          latestQrSvg = '';
        }
        if (state !== 'connected') {
          state = 'qr_ready';
        }
      }

      if (connection === 'open') {
        state = 'connected';
        loggedOutRemotely = false;
        latestQr = '';
        latestQrSvg = '';
        latestPairingCode = '';
        lastError = '';
        const rawId = sock?.user?.id || authState.creds?.me?.id || '';
        const numMatch = rawId.match(/^(\d+)/);
        connectedPhone = numMatch ? `+${numMatch[1]}` : rawId;
        connectedName = sock?.user?.name || authState.creds?.me?.name || 'WhatsApp Linked Device';
      }

      if (connection === 'close') {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const loggedOut = statusCode === DisconnectReason.loggedOut;
        connectedPhone = '';
        connectedName = '';
        if (loggedOut) {
          state = 'disconnected';
          loggedOutRemotely = true;
          latestQr = '';
          latestQrSvg = '';
          try { fs.rmSync(AUTH_DIR, { recursive: true, force: true }); } catch {}
        } else {
          state = 'connecting';
          if (reconnectTimer) clearTimeout(reconnectTimer);
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            if (state !== 'disconnected') void startSocket();
          }, 1500);
        }
      }
    });

    if (pairPhone && !authState.creds?.registered) {
      const digits = pairPhone.replace(/\D/g, '');
      if (digits.length >= 7) {
        setTimeout(async () => {
          try {
            if (sock && typeof sock.requestPairingCode === 'function') {
              const code = await sock.requestPairingCode(digits);
              latestPairingCode = code;
            }
          } catch (err) {
            lastError = String(err?.message || err);
          }
        }, 1200);
      }
    }
  } catch (err) {
    state = 'error';
    lastError = String(err?.message || err);
  } finally {
    starting = false;
  }
}

function readJson(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); }
      catch { resolve({}); }
    });
  });
}

function sendJson(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

const server = http.createServer(async (req, res) => {
  const url = (req.url || '/').split('?')[0];

  if (req.method === 'GET' && url === '/status') {
    return sendJson(res, 200, {
      state,
      connected: state === 'connected',
      logged_out: loggedOutRemotely,
      qr: latestQr,
      qr_svg: latestQrSvg,
      pairing_code: latestPairingCode,
      phone: connectedPhone,
      device_name: connectedName,
      error: lastError,
    });
  }

  if (req.method === 'POST' && url === '/start') {
    const body = await readJson(req);
    const phone = String(body.phone || '').trim();
    loggedOutRemotely = false;
    if (state !== 'connected') {
      await startSocket(phone);
      // Wait briefly for initial QR / pairing code emission
      for (let i = 0; i < 20; i++) {
        if (latestQrSvg || latestPairingCode || state === 'connected' || state === 'error') break;
        await new Promise((r) => setTimeout(r, 250));
      }
    }
    return sendJson(res, 200, {
      status: state === 'connected' ? 'connected' : (latestQrSvg ? 'ready_to_scan' : state),
      state,
      connected: state === 'connected',
      qr: latestQr,
      qr_svg: latestQrSvg,
      pairing_code: latestPairingCode,
      phone: connectedPhone,
      device_name: connectedName,
      error: lastError,
    });
  }

  if (req.method === 'POST' && url === '/send') {
    const body = await readJson(req);
    const phone = String(body.phone || '').trim();
    const text = String(body.text || '').trim();
    if (state !== 'connected' || !sock) {
      return sendJson(res, 400, {
        status: 'error',
        message: 'WhatsApp is not connected. Scan the QR code or link your device first.',
      });
    }
    const digits = phone.replace(/\D/g, '');
    if (digits.length < 7) {
      return sendJson(res, 400, {
        status: 'error',
        message: 'Enter a valid recipient phone number with country code (e.g. +919810795310).',
      });
    }
    try {
      const jid = resolveTargetJid(digits);
      const result = await enqueueSend(() => sock.sendMessage(jid, { text }));
      trackSentMessage(result);
      return sendJson(res, 200, {
        status: 'delivered',
        channel: 'whatsapp',
        recipient: `+${digits}`,
        message_id: result?.key?.id || `wa_${Date.now()}`,
        live_network: true,
      });
    } catch (err) {
      return sendJson(res, 500, {
        status: 'error',
        message: String(err?.message || err),
      });
    }
  }

  if (req.method === 'GET' && url === '/inbox') {
    const items = inboxQueue.splice(0, inboxQueue.length);
    return sendJson(res, 200, { status: 'ok', messages: items });
  }

  if (req.method === 'GET' && url === '/debug') {
    return sendJson(res, 200, {
      state,
      connectedPhone,
      user: sock?.user || null,
      inbox_len: inboxQueue.length,
      recent_events: recentEvents,
    });
  }

  if (req.method === 'POST' && url === '/send-document') {
    const body = await readJson(req);
    const phone = String(body.phone || '').trim();
    const filePath = String(body.file_path || '').trim();
    const caption = String(body.caption || '').trim();
    if (state !== 'connected' || !sock) {
      return sendJson(res, 400, { status: 'error', message: 'WhatsApp is not connected.' });
    }
    const digits = phone.replace(/\D/g, '');
    if (digits.length < 7) {
      return sendJson(res, 400, { status: 'error', message: 'Valid recipient phone number required.' });
    }
    if (!filePath || !fs.existsSync(filePath)) {
      return sendJson(res, 400, { status: 'error', message: `File not found: ${filePath}` });
    }
    try {
      const jid = resolveTargetJid(digits);
      const fileName = path.basename(filePath);
      const mimetype = fileName.endsWith('.apk') ? 'application/vnd.android.package-archive' : 'application/octet-stream';
      const docBuffer = fs.readFileSync(filePath);
      const result = await enqueueSend(() => sock.sendMessage(jid, {
        document: docBuffer,
        mimetype,
        fileName,
        caption,
      }));
      trackSentMessage(result);
      return sendJson(res, 200, {
        status: 'uploaded',
        channel: 'whatsapp',
        recipient: `+${digits}`,
        file_name: fileName,
        message_id: result?.key?.id || `wa_doc_${Date.now()}`,
        live_network: true,
      });
    } catch (err) {
      return sendJson(res, 500, { status: 'error', message: String(err?.message || err) });
    }
  }

  if (req.method === 'POST' && url === '/disconnect') {
    try {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (sock) {
        const activeSock = sock;
        sock = null;
        try { await activeSock.logout(); } catch {}
        try { activeSock.end(undefined); } catch {}
      }
      sentByRaaIds.clear();
      sentMessageStore.clear();
      phoneDigitsToChatJid.clear();
      state = 'disconnected';
      latestQr = '';
      latestQrSvg = '';
      latestPairingCode = '';
      connectedPhone = '';
      connectedName = '';
      try { fs.rmSync(AUTH_DIR, { recursive: true, force: true }); } catch {}
      return sendJson(res, 200, { status: 'disconnected', paired: false });
    } catch (err) {
      return sendJson(res, 500, { status: 'error', message: String(err?.message || err) });
    }
  }

  sendJson(res, 404, { status: 'error', message: 'Not found' });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`RAA WhatsApp Baileys bridge listening on http://127.0.0.1:${PORT}`);
  if (fs.existsSync(path.join(AUTH_DIR, 'creds.json'))) {
    void startSocket();
  }
});
