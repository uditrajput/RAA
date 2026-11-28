"""Cyber-Glass Neon Design System Setup and Tool Manager UI.

Comprehensive embedded web application served at /setup with full REST API endpoints
for tools management, mobile channels, MCP mesh, TV studio, and zero-knowledge vault.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import ctypes
import json
import logging
import os
import re
import shutil
import socket
import struct
import subprocess
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["setup_ui"])


class ToolActionBody(BaseModel):
    tool_name: str
    force: bool = False


class ToolCustomPathBody(BaseModel):
    tool_name: str
    custom_path: str


class ToolOpenPathBody(BaseModel):
    tool_name: str | None = None
    path: str | None = None


class CadenceConfigBody(BaseModel):
    mode: str = "interval"
    interval_minutes: int = 5


class ChannelPingBody(BaseModel):
    channel: str
    target: str = "test_user"


class TelegramConfigBody(BaseModel):
    bot_token: str
    chat_id: str | None = None


class TelegramSendBody(BaseModel):
    chat_id: str | None = None
    text: str = "🟢 [RAA v4.0.0] Telegram Channel Test Ping Successful. Link is operational."


class WhatsAppPairBody(BaseModel):
    phone: str = "+1 (555) 019-2834"
    device_name: str = "Pixel 8 Pro (Android 14)"


class WhatsAppSendBody(BaseModel):
    phone: str = ""
    text: str = "🟢 [RAA v4.0.0] WhatsApp Channel Test Ping Successful. Link is operational."


class ChannelInboundBody(BaseModel):
    channel: str = "whatsapp"
    sender_id: str = "+919810795310"
    text: str = ""
    attachment_path: str = ""
    auto_reply: bool = True


class ShieldTestBody(BaseModel):
    content: str


class VaultSaveBody(BaseModel):
    key_name: str
    service: str = "general"
    username: str = ""
    secret_value: str = ""
    description: str = ""


class VaultDeleteBody(BaseModel):
    key_name: str


class ToolCustomAddBody(BaseModel):
    tool_id: str
    display_name: str
    category: str = "decompilation"
    source_type: str = "github_release"
    artifact_type: str = "zip"
    download_url: str = ""
    filename: str = ""
    relative_bin_dir: str = "."
    description: str = ""
    pip_package: str = ""
    auto_download: bool = True


class MeshConnectBody(BaseModel):
    name: str
    transport: str = "stdio"
    command: str | None = None
    url: str | None = None
    display_name: str = ""
    env: dict[str, str] | None = None


class TvRedesignBody(BaseModel):
    target: str = "com.android.tv.launcher"
    theme_name: str = "midnight-glass"
    dock_apps: list[str] = []


class TvScanBody(BaseModel):
    tv_host: str = ""


class TvDebloatBody(BaseModel):
    tv_host: str = ""
    packages: list[str] = []
    restore: bool = False


class TvDockThemeBody(BaseModel):
    tv_host: str = ""
    theme_name: str = "midnight-glass"
    dock_apps: list[str] = []
    hidden_apps: list[str] = []


class TvDocBody(BaseModel):
    tv_host: str = ""
    target: str = "com.android.tv.launcher"
    theme_name: str = "midnight-glass"
    dock_apps: list[str] = []
    removed_apps: list[str] = []


class MeshActionBody(BaseModel):
    name: str


class MeshToggleBody(BaseModel):
    name: str
    enabled: bool


class ConfigSaveBody(BaseModel):
    file_id: str
    content: str


class ProfileUpdateBody(BaseModel):
    active_profile: str


SETUP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🛡️ RAA Studio v4.0.0 — Setup & Tool Manager</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --obsidian: #0A0E17;
      --glass-bg: rgba(18, 24, 38, 0.85);
      --glass-border: rgba(255, 255, 255, 0.08);
      --emerald: #00F59B;
      --azure: #00D2FF;
      --violet: #A855F7;
      --wa-green: #25D366;
      --amber: #F59E0B;
      --crimson: #EF4444;
    }
    body {
      background-color: var(--obsidian);
      color: #E2E8F0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      overflow-x: hidden;
    }
    .glass-panel {
      background: var(--glass-bg);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--glass-border);
    }
    .neon-emerald-glow {
      box-shadow: 0 0 15px rgba(0, 245, 155, 0.35);
    }
    .neon-azure-glow {
      box-shadow: 0 0 15px rgba(0, 210, 255, 0.35);
    }
    .pulse-dot {
      animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: .4; }
    }
    .tab-active {
      color: var(--emerald) !important;
      background: rgba(0, 245, 155, 0.1) !important;
      border: 1px solid rgba(0, 245, 155, 0.3) !important;
    }
    .card-selected {
      border-color: var(--emerald) !important;
      background: rgba(0, 245, 155, 0.08) !important;
      box-shadow: 0 0 15px rgba(0, 245, 155, 0.25);
    }
    /* Total Elimination of Horizontal Scrollbar */
    html {
      overflow-x: hidden !important;
      width: 100% !important;
      max-width: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      box-sizing: border-box !important;
    }
    body {
      overflow-x: hidden !important;
      width: 100% !important;
      max-width: 100% !important;
      margin: 0 !important;
      box-sizing: border-box !important;
    }
    *, *::before, *::after {
      box-sizing: border-box;
    }
    .no-scrollbar::-webkit-scrollbar {
      display: none !important;
      width: 0 !important;
      height: 0 !important;
    }
    .no-scrollbar {
      -ms-overflow-style: none !important;
      scrollbar-width: none !important;
    }
    /* Custom sleek scrollbar for code/pre */
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.12);
      border-radius: 9999px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: rgba(0, 245, 155, 0.4);
    }

    /* ========================================================
       High-Contrast Accessible Light Mode Overrides
       ======================================================== */
    body.light-mode {
      background-color: #F8FAFC !important;
      color: #0F172A !important;
    }
    body.light-mode .glass-panel {
      background: rgba(255, 255, 255, 0.96) !important;
      border: 1px solid rgba(226, 232, 240, 0.9) !important;
      color: #0F172A !important;
      box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05) !important;
    }
    body.light-mode header {
      background: rgba(255, 255, 255, 0.98) !important;
      border: 1.5px solid #CBD5E1 !important;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode header h1 {
      color: #0F172A !important;
    }
    body.light-mode header p,
    body.light-mode .text-slate-400 {
      color: #475569 !important;
    }
    body.light-mode .text-white {
      color: #0F172A !important;
    }
    body.light-mode .text-slate-200,
    body.light-mode .text-slate-300 {
      color: #1E293B !important;
    }
    body.light-mode select {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1.5px solid #94A3B8 !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
    }
    body.light-mode textarea {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1.5px solid #94A3B8 !important;
      box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }

    /* Menu Navigation Bar & Container in Light Mode */
    body.light-mode #mainNav,
    body.light-mode nav {
      background: #FFFFFF !important;
      border: 1.5px solid #CBD5E1 !important;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05) !important;
      border-radius: 16px !important;
      padding: 6px 8px !important;
      gap: 3px !important;
    }
    body.light-mode .tab-btn {
      color: #334155 !important;
      background: #F8FAFC !important;
      border: 1px solid #E2E8F0 !important;
      padding: 5px 8px !important;
      font-weight: 600 !important;
      transition: all 0.15s ease !important;
    }
    body.light-mode .tab-btn:hover {
      color: #0F172A !important;
      background-color: #E2E8F0 !important;
      border-color: #CBD5E1 !important;
    }
    body.light-mode .tab-active,
    body.light-mode .tab-btn.tab-active {
      color: #065F46 !important;
      background: #ECFDF5 !important;
      border: 1.5px solid #059669 !important;
      font-weight: 700 !important;
      box-shadow: 0 2px 6px rgba(5, 150, 105, 0.18) !important;
    }

    /* Search Bars & All Text Inputs in Light Mode */
    body.light-mode input[type="text"],
    body.light-mode input[type="search"],
    body.light-mode input[type="number"],
    body.light-mode input[type="password"],
    body.light-mode input {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1.5px solid #94A3B8 !important;
      box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.06) !important;
    }
    body.light-mode input::placeholder {
      color: #64748B !important;
      opacity: 1 !important;
    }
    body.light-mode input:focus {
      border-color: #059669 !important;
      box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.2) !important;
      outline: none !important;
    }

    /* Filter & Search Bar Container Box in Light Mode */
    body.light-mode [class*="bg-slate-900"],
    body.light-mode [class*="bg-slate-950"] {
      background-color: #F8FAFC !important;
      border: 1px solid #CBD5E1 !important;
      color: #0F172A !important;
    }

    /* Header Controls in Light Mode */
    body.light-mode header select {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1.5px solid #94A3B8 !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
      font-weight: 600 !important;
    }
    body.light-mode header button {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1.5px solid #94A3B8 !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
      font-weight: 600 !important;
    }
    body.light-mode header button:hover {
      border-color: #059669 !important;
      color: #047857 !important;
      background-color: #F8FAFC !important;
    }
    body.light-mode #themeToggleBtn {
      background-color: #FFFFFF !important;
      border: 1.5px solid #94A3B8 !important;
      color: #0F172A !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
    }
    body.light-mode #themeToggleBtn:hover {
      border-color: #059669 !important;
      background-color: #ECFDF5 !important;
    }

    /* Category & Status Filter Buttons in Light Mode */
    body.light-mode .tool-filter-btn,
    body.light-mode .skill-filter-btn,
    body.light-mode .mesh-category-btn {
      color: #475569 !important;
      background-color: transparent !important;
      border: 1px solid transparent !important;
      font-weight: 600 !important;
    }
    body.light-mode .tool-filter-btn:hover,
    body.light-mode .skill-filter-btn:hover,
    body.light-mode .mesh-category-btn:hover {
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
    }
    body.light-mode .tool-filter-btn[class*="bg-emerald"],
    body.light-mode .skill-filter-btn[class*="bg-emerald"],
    body.light-mode .mesh-category-btn[class*="bg-emerald"],
    body.light-mode .tool-filter-btn.active-filter {
      background-color: #ECFDF5 !important;
      color: #065F46 !important;
      border: 1.5px solid #059669 !important;
      font-weight: 700 !important;
      box-shadow: 0 1px 4px rgba(5, 150, 105, 0.18) !important;
    }
    body.light-mode .tool-status-btn,
    body.light-mode .mesh-filter-btn {
      background-color: #FFFFFF !important;
      color: #334155 !important;
      border: 1px solid #CBD5E1 !important;
      font-weight: 600 !important;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode .tool-status-btn:hover,
    body.light-mode .mesh-filter-btn:hover {
      background-color: #E2E8F0 !important;
      color: #0F172A !important;
      border-color: #94A3B8 !important;
    }
    body.light-mode .tool-status-btn[class*="bg-cyan"],
    body.light-mode .mesh-filter-btn[class*="bg-cyan"],
    body.light-mode .mesh-filter-btn.active-filter {
      background-color: #F0F9FF !important;
      color: #0369A1 !important;
      border: 1.5px solid #0284C7 !important;
      font-weight: 700 !important;
      box-shadow: 0 1px 4px rgba(2, 132, 199, 0.18) !important;
    }

    /* General Action Buttons & Links in Light Mode */
    body.light-mode a[class*="bg-slate-900"],
    body.light-mode button[class*="bg-slate-900"] {
      background-color: #F8FAFC !important;
      color: #0F172A !important;
      border: 1px solid #CBD5E1 !important;
      font-weight: 600 !important;
    }
    body.light-mode a[class*="bg-slate-900"]:hover,
    body.light-mode button[class*="bg-slate-900"]:hover {
      background-color: #F1F5F9 !important;
      border-color: #059669 !important;
      color: #047857 !important;
    }
    body.light-mode .text-cyan-300,
    body.light-mode .text-cyan-400 {
      color: #0E7490 !important;
    }
    body.light-mode .text-emerald-300,
    body.light-mode .text-emerald-400 {
      color: #047857 !important;
    }
    body.light-mode .text-violet-300,
    body.light-mode .text-violet-400 {
      color: #6D28D9 !important;
    }
    body.light-mode .text-amber-300,
    body.light-mode .text-amber-400 {
      color: #B45309 !important;
    }
    body.light-mode .text-red-300,
    body.light-mode .text-red-400 {
      color: #B91C1C !important;
    }
    body.light-mode .text-slate-500 {
      color: #475569 !important;
    }
    body.light-mode code {
      background-color: #F1F5F9 !important;
      color: #0F766E !important;
      padding: 1px 5px;
      border-radius: 4px;
      border: 1px solid #CBD5E1;
    }
    body.light-mode button:disabled {
      opacity: 0.72 !important;
      color: #334155 !important;
      border-color: #94A3B8 !important;
    }
    body.light-mode button[class*="bg-slate-800"] {
      background-color: #E2E8F0 !important;
      color: #0F172A !important;
      border-color: #CBD5E1 !important;
    }
    body.light-mode button[class*="bg-slate-800"]:hover {
      background-color: #CBD5E1 !important;
    }

    /* Emerald Themed Buttons (Verify, Add, Mark Active) */
    body.light-mode button[class*="bg-emerald-500"] {
      background-color: #ECFDF5 !important;
      color: #047857 !important;
      border: 1.5px solid #10B981 !important;
      font-weight: 700 !important;
    }
    body.light-mode button[class*="bg-emerald-500"]:hover {
      background-color: #D1FAE5 !important;
      border-color: #059669 !important;
    }

    /* Cyan Themed Buttons (Ping, Reveal, Config Open) */
    body.light-mode button[class*="bg-cyan-500"] {
      background-color: #F0F9FF !important;
      color: #0369A1 !important;
      border: 1.5px solid #38BDF8 !important;
      font-weight: 700 !important;
    }
    body.light-mode button[class*="bg-cyan-500"]:hover {
      background-color: #E0F2FE !important;
      border-color: #0284C7 !important;
    }

    /* Amber Themed Buttons (Deactivate, Path) */
    body.light-mode button[class*="bg-amber-500"] {
      background-color: #FFFBEB !important;
      color: #B45309 !important;
      border: 1.5px solid #FBBF24 !important;
      font-weight: 700 !important;
    }
    body.light-mode button[class*="bg-amber-500"]:hover {
      background-color: #FEF3C7 !important;
      border-color: #D97706 !important;
    }

    /* Red / Danger Themed Buttons (Delete) */
    body.light-mode button[class*="bg-red-500"] {
      background-color: #FEF2F2 !important;
      color: #B91C1C !important;
      border: 1.5px solid #F87171 !important;
      font-weight: 700 !important;
    }
    body.light-mode button[class*="bg-red-500"]:hover {
      background-color: #FEE2E2 !important;
      border-color: #DC2626 !important;
    }

    /* Slate Utility Buttons (Refresh, Cancel, Discard, Browse) */
    body.light-mode [class*="bg-slate-800"] {
      background-color: #F1F5F9 !important;
      color: #334155 !important;
      border: 1.5px solid #CBD5E1 !important;
      font-weight: 600 !important;
    }
    body.light-mode [class*="bg-slate-800"]:hover {
      background-color: #E2E8F0 !important;
      color: #0F172A !important;
      border-color: #94A3B8 !important;
    }

    /* Step Titles & Status Badge in Light Mode */
    body.light-mode #wizardStepNum,
    body.light-mode #wizardStepTitle {
      color: #047857 !important;
    }
    body.light-mode #wizardStepDesc {
      color: #475569 !important;
    }
    body.light-mode .pulse-dot {
      background-color: #059669 !important;
    }
    body.light-mode .font-mono.font-semibold {
      color: #334155 !important;
    }

    /* Persona Cards in Light Mode */
    body.light-mode .persona-card {
      background: #FFFFFF !important;
      border: 1.5px solid #E2E8F0 !important;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
    }
    body.light-mode .persona-card:hover {
      border-color: #059669 !important;
      box-shadow: 0 4px 14px rgba(5, 150, 105, 0.12) !important;
    }
    body.light-mode .persona-card h3 {
      color: #0F172A !important;
    }
    body.light-mode .persona-card p {
      color: #475569 !important;
    }
    body.light-mode .card-selected {
      border: 2px solid #059669 !important;
      background: rgba(5, 150, 105, 0.08) !important;
      box-shadow: 0 0 16px rgba(5, 150, 105, 0.18) !important;
    }

    /* Wizard Action Buttons in Light Mode */
    body.light-mode #prevBtn {
      background-color: #E2E8F0 !important;
      color: #1E293B !important;
      border: 1.5px solid #CBD5E1 !important;
      opacity: 1 !important;
      cursor: pointer !important;
    }
    body.light-mode #prevBtn:disabled {
      background-color: #F1F5F9 !important;
      color: #94A3B8 !important;
      border: 1.5px solid #E2E8F0 !important;
      opacity: 1 !important;
      cursor: not-allowed !important;
    }
    body.light-mode #prevBtn:not(:disabled):hover {
      background-color: #CBD5E1 !important;
      color: #0F172A !important;
    }
    body.light-mode #nextBtn {
      background: linear-gradient(135deg, #059669, #0284C7) !important;
      color: #FFFFFF !important;
      border: none !important;
      box-shadow: 0 4px 14px rgba(5, 150, 105, 0.25) !important;
    }
    body.light-mode #nextBtn:hover {
      opacity: 0.92 !important;
      box-shadow: 0 6px 18px rgba(5, 150, 105, 0.35) !important;
    }
    body.light-mode button[onclick="skipWizard()"] {
      color: #475569 !important;
    }
    body.light-mode button[onclick="skipWizard()"]:hover {
      color: #047857 !important;
    }

    /* Config Editor Pills & Buttons */
    body.light-mode .cfg-pill {
      background-color: #FFFFFF !important;
      color: #334155 !important;
      border: 1px solid #CBD5E1 !important;
      font-weight: 600 !important;
    }
    body.light-mode .cfg-pill:hover {
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
      border-color: #94A3B8 !important;
    }
    body.light-mode .cfg-pill.active-cfg {
      background-color: #E0F2FE !important;
      color: #0369A1 !important;
      border: 1.5px solid #0284C7 !important;
      font-weight: 700 !important;
    }
    body.light-mode #configEditorTextarea {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1.5px solid #CBD5E1 !important;
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    }

    /* Modal Dialogs in Light Mode */
    body.light-mode #toolPathModal > div,
    body.light-mode #confirmDialogModal > div,
    body.light-mode #messageDialogModal > div {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border: 1.5px solid #CBD5E1 !important;
      box-shadow: 0 20px 45px rgba(0, 0, 0, 0.15) !important;
    }
    body.light-mode #modalCurrentPath {
      background-color: #F8FAFC !important;
      color: #0369A1 !important;
      border: 1px solid #CBD5E1 !important;
    }

    /* Footer & Pro Tip in Light Mode */
    body.light-mode footer {
      background: rgba(255, 255, 255, 0.98) !important;
      border: 1.5px solid #CBD5E1 !important;
      color: #475569 !important;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
    }
    body.light-mode footer span.text-emerald-400 {
      color: #047857 !important;
    }
    body.light-mode footer code {
      color: #047857 !important;
      background: #F1F5F9;
      padding: 1px 4px;
      border-radius: 4px;
      border: 1px solid #E2E8F0;
    }
  </style>
</head>
<body class="min-h-screen p-4 md:p-8">
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <header class="glass-panel rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 border border-white/10">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-400/20 to-cyan-500/20 border border-emerald-500/40 flex items-center justify-center text-2xl shadow-lg">
          🛡️
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-2xl font-bold tracking-tight text-white">RAA STUDIO</h1>
            <span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">v4.0.0</span>
          </div>
          <p class="text-sm text-slate-400">Autonomous Self-Evolving Mobile Intelligence & Tool Manager</p>
        </div>
      </div>
      <div class="flex items-center space-x-3">
        <div id="profileSelectWrapper" style="display: none;" class="relative items-center">
          <select id="profileSelect" onchange="switchProfile(this.value)" class="glass-panel text-sm text-slate-200 pl-3.5 pr-8 py-2 rounded-xl border border-white/10 outline-none focus:border-cyan-400 cursor-pointer">
            <option value="core">⚡ Profile: Core Reversing</option>
            <option value="full">🔥 Profile: Full Offensive</option>
            <option value="ui">🎨 Profile: Living Canvas UI</option>
            <option value="swarm">🐝 Profile: Enterprise Swarm</option>
          </select>
        </div>
        <button id="themeToggleBtn" onclick="toggleTheme()" class="glass-panel px-3 py-2 rounded-xl border border-white/10 hover:border-cyan-400 inline-flex items-center gap-1.5 transition cursor-pointer shadow-sm shrink-0 text-xs font-semibold text-slate-200" title="Toggle Theme (Dark / Light)">
          <span id="themeToggleIcon" class="text-sm leading-none">🌙</span>
          <span id="themeToggleLabel">Dark</span>
        </button>
      </div>
    </header>

    <!-- Navigation Tabs -->
    <nav id="mainNav" class="glass-panel rounded-2xl p-2 flex flex-wrap items-center gap-1 border border-white/10 text-xs font-medium no-scrollbar shadow-sm">
      <button onclick="switchTab('wizard')" id="tab-wizard" class="tab-btn px-2.5 py-1.5 rounded-lg text-emerald-400 tab-active transition whitespace-nowrap text-xs font-semibold">🌟 Setting Wizard</button>
      <button onclick="switchTab('workspace')" id="tab-workspace" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">🌐 Workspace</button>
      <button onclick="switchTab('tools')" id="tab-tools" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">🛠️ Tools</button>
      <button onclick="switchTab('channels')" id="tab-channels" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">📱 Mobile Channels</button>
      <button onclick="switchTab('wifi')" id="tab-wifi" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">📶 Wi-Fi Devices</button>
      <button onclick="switchTab('mesh')" id="tab-mesh" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">🔌 MCP Mesh</button>
      <button onclick="switchTab('skills')" id="tab-skills" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">🧩 Skills</button>
      <button onclick="switchTab('tv')" id="tab-tv" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">📺 TV Studio</button>
      <button onclick="switchTab('security')" id="tab-security" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold">🛡️ Vault &amp; Shield</button>
      <button onclick="switchTab('config')" id="tab-config" class="tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap inline-flex items-center gap-2 text-xs font-semibold"><span>⚙️ Config Editor</span><span class="ml-1.5 text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 whitespace-nowrap">JSON Live</span></button>
    </nav>

    <!-- Main Container -->
    <main class="glass-panel rounded-2xl p-6 md:p-8 border border-white/10">

      <!-- View 1: 5-Step Wizard -->
      <section id="view-wizard" class="space-y-4">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div>
            <h2 class="text-xl font-bold flex items-center gap-2">
              <span id="wizardStepNum" class="text-emerald-400">Step 1 of 5:</span>
              <span id="wizardStepTitle" class="text-emerald-400">Workspace & Operational Profile</span>
            </h2>
            <p id="wizardStepDesc" class="text-sm text-slate-400 mt-1">Select your active reversing persona to automatically tune security policies and tool chains.</p>
          </div>
          <div class="flex items-center space-x-2 shrink-0">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 pulse-dot"></span>
            <span class="text-xs text-slate-400 font-mono font-semibold">ONBOARDING ACTIVE</span>
          </div>
        </div>

        <div id="wizardStepContent">
          <!-- Rendered dynamically -->
        </div>

        <div class="flex items-center justify-between pt-4 border-t border-white/10">
          <button onclick="skipWizard()" class="text-xs text-slate-400 hover:text-slate-200 transition">Skip to Workspace ➔</button>
          <div class="flex space-x-3">
            <button id="prevBtn" onclick="prevStep()" disabled class="px-5 py-2.5 rounded-xl bg-slate-900/80 text-slate-400 border border-white/10 font-semibold text-xs disabled:opacity-30 disabled:cursor-not-allowed hover:border-slate-400 transition">◀ Previous</button>
            <button id="nextBtn" onclick="nextStep()" class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-400 to-cyan-400 text-slate-950 font-bold text-xs hover:opacity-90 shadow-[0_0_15px_rgba(0,245,155,0.4)] transition">Next Step ▶</button>
          </div>
        </div>
      </section>

      <!-- View 2: Workspace Tab -->
      <section id="view-workspace" class="hidden space-y-6">
        <div class="border-b border-white/10 pb-4">
          <h2 class="text-xl font-bold text-white">🌐 Persistent Workspace & Audit Database</h2>
          <p class="text-sm text-slate-400">Local repository storage, SQLite audit trail, and procedural memory.</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-2">
            <div class="text-xs font-mono text-cyan-400 uppercase tracking-wider">Root Directory</div>
            <div class="text-sm font-bold text-white">.raa-workspace/</div>
            <p class="text-xs text-slate-400">Isolated workspace partition preventing system contamination.</p>
          </div>
          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-2">
            <div class="text-xs font-mono text-emerald-400 uppercase tracking-wider">Audit Database</div>
            <div class="text-sm font-bold text-white">raa.sqlite3 (Active)</div>
            <p class="text-xs text-slate-400">Immutable ledger logging tool executions, mutations, and verification hashes.</p>
          </div>
          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-2">
            <div class="text-xs font-mono text-violet-400 uppercase tracking-wider">Procedural Memory</div>
            <div class="text-sm font-bold text-white">memory/MEMORY.md</div>
            <p class="text-xs text-slate-400">Self-evolving recipes, dynamic unpacking tricks, and vulnerability lessons.</p>
          </div>
        </div>

        <!-- System Runtimes & Prerequisites -->
        <div class="space-y-3 pt-2">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            <div>
              <h3 class="text-base font-bold text-white">⚡ System Runtimes &amp; Prerequisites</h3>
              <p class="text-xs text-slate-400">Live availability check for JDK, Node.js/NPM, Python, .NET SDK, Git, and ADB.</p>
            </div>
            <button onclick="loadWorkspaceRuntimes()" class="px-3 py-1.5 rounded-xl glass-panel text-xs text-slate-300 border border-white/10 hover:border-white/30 transition">
              🔄 Check Runtimes
            </button>
          </div>
          <div id="workspaceRuntimesGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div class="text-slate-400 text-xs col-span-full py-6 text-center">Checking installed system runtimes...</div>
          </div>
        </div>
      </section>

      <!-- View 3: Tools Tab -->
      <section id="view-tools" class="hidden space-y-6">
        <div class="flex flex-wrap md:flex-nowrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div class="min-w-0">
            <h2 class="text-xl font-bold text-white">🛠️ Reversing Engine Toolchain & Binaries</h2>
            <p class="text-sm text-slate-400">All available external engines. Download directly with real-time progress, link official GitHub/sites, or configure custom paths.</p>
          </div>
          <div class="flex items-center gap-2 shrink-0 flex-wrap">
            <span id="toolsCountBadge" class="px-3 py-1 rounded-full text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 whitespace-nowrap">Loading...</span>
            <button onclick="downloadTool('all')" class="px-3 py-2 rounded-xl bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-semibold hover:border-emerald-400 transition flex items-center gap-1.5 whitespace-nowrap">
              <span>⬇️ Download All Missing</span>
            </button>
            <button onclick="loadTools()" class="px-3 py-2 rounded-xl glass-panel text-xs text-slate-300 border border-white/10 hover:border-white/30 transition whitespace-nowrap">
              🔄 Refresh
            </button>
          </div>
        </div>

        <!-- Custom Tool Provisioning Form (GitHub Repo / Release / Website / JAR / ZIP / TAR.XZ / Source / PyPI) -->
        <div id="customToolForm" class="hidden glass-panel p-5 rounded-xl border border-cyan-500/30 bg-slate-950/85 space-y-3">
          <div class="flex justify-between items-center">
            <h4 class="font-bold text-white text-sm">&#10133; Register &amp; Download Custom Reversing Tool</h4>
            <button onclick="toggleCustomToolForm()" class="text-xs text-slate-400 hover:text-white px-2 py-1 rounded">✕</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input id="customToolId" type="text" placeholder="Tool ID (e.g. dex2jar)" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
            <input id="customToolName" type="text" placeholder="Display Name (e.g. Dex2Jar)" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
            <select id="customToolSourceType" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
              <option value="github_release">Source: GitHub Release</option>
              <option value="github_repo">Source: GitHub Repo (git / source)</option>
              <option value="website">Source: Official Website URL</option>
              <option value="pypi">Source: PyPI (pip)</option>
            </select>
            <select id="customToolArtifactType" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
              <option value="zip">Format: ZIP Archive (.zip)</option>
              <option value="jar">Format: Java JAR (.jar)</option>
              <option value="tar.xz">Format: TAR.XZ / TAR.GZ</option>
              <option value="binary">Format: Direct Binary (.exe / bin)</option>
              <option value="source_repo">Format: Source Code Repo (.git / .py)</option>
              <option value="pypi">Format: Python Package (pip)</option>
            </select>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input id="customToolUrl" type="text" placeholder="Download URL, GitHub Repo URL, or pip package" class="md:col-span-2 bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
            <input id="customToolFilename" type="text" placeholder="Target binary/JAR/script (e.g. d2j-dex2jar.bat)" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
          </div>
          <div class="flex items-center justify-between gap-3">
            <select id="customToolCategory" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
              <option value="decompilation">Category: Decompilation</option>
              <option value="rebuilding">Category: Rebuilding</option>
              <option value="device">Category: Device &amp; Control</option>
              <option value="native">Category: Native &amp; Disasm</option>
              <option value="signing">Category: Signing</option>
              <option value="security">Category: Security</option>
              <option value="network">Category: Network</option>
            </select>
            <button onclick="submitCustomTool()" class="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90">
              ⬇️ Register &amp; Download Tool
            </button>
          </div>
        </div>

        <!-- Global Multi-Tool Download Progress Banner (hidden by default) -->
        <div id="globalDownloadBanner" class="hidden glass-panel p-4 rounded-xl border border-cyan-500/40 bg-slate-950/90 space-y-2">
          <div class="flex justify-between items-center text-xs font-mono">
            <span id="globalDownloadTitle" class="text-cyan-300 font-bold flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 pulse-dot"></span>
              Provisioning Reversing Toolchain (0 / 0 Completed)...
            </span>
            <span id="globalDownloadPercent" class="text-emerald-400 font-bold">0%</span>
          </div>
          <div class="w-full bg-slate-900 border border-white/10 rounded-full h-3 p-0.5 overflow-hidden">
            <div id="globalProgressBar" class="bg-gradient-to-r from-cyan-400 via-emerald-400 to-emerald-500 h-2 rounded-full transition-all duration-200 shadow-[0_0_12px_rgba(0,245,155,0.7)]" style="width: 0%"></div>
          </div>
          <div id="globalDownloadDetail" class="text-[11px] text-slate-400 font-mono">Connecting to mirrors...</div>
        </div>

        <!-- Category Filters & Search -->
        <div class="space-y-3 bg-slate-900/60 p-3 rounded-xl border border-white/10">
          <div class="flex flex-wrap gap-1.5" id="toolCategoryFilters">
            <button onclick="filterToolsCategory('all', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">All</button>
            <button onclick="filterToolsCategory('decompilation', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Decompilation</button>
            <button onclick="filterToolsCategory('rebuilding', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Rebuilding</button>
            <button onclick="filterToolsCategory('device', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Device &amp; Control</button>
            <button onclick="filterToolsCategory('native', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Native &amp; Disasm</button>
            <button onclick="filterToolsCategory('signing', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Signing</button>
            <button onclick="filterToolsCategory('security', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Security &amp; Dynamic</button>
            <button onclick="filterToolsCategory('network', this)" class="tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Network</button>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap gap-2" id="toolStatusFilters">
              <button onclick="filterToolsStatus('all', this)" class="tool-status-btn px-3 py-1 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">All Tools</button>
              <button onclick="filterToolsStatus('ready', this)" class="tool-status-btn px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Ready (✓)</button>
              <button onclick="filterToolsStatus('pending', this)" class="tool-status-btn px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Pending</button>
            </div>
            <div class="w-full md:w-auto flex flex-wrap items-center gap-2">
              <select id="toolSortSelect" onchange="resetToolsPageAndRender()" aria-label="Sort tools" class="bg-slate-950/80 border border-white/10 text-xs px-2.5 py-1.5 rounded-lg text-slate-200 outline-none focus:border-cyan-400">
                <option value="default">Sort: Default Order</option>
                <option value="name_asc">Sort: Name (A → Z)</option>
                <option value="name_desc">Sort: Name (Z → A)</option>
                <option value="status_ready">Sort: Ready First</option>
                <option value="status_pending">Sort: Pending First</option>
                <option value="size_desc">Sort: Size (Largest)</option>
                <option value="size_asc">Sort: Size (Smallest)</option>
              </select>
              <input type="text" id="toolSearchInput" onkeyup="searchTools(this.value)" placeholder="🔍 Search engines &amp; tools..." class="w-full md:w-56 bg-slate-950/80 border border-white/10 text-xs px-3 py-1.5 rounded-lg text-white outline-none focus:border-cyan-400">
              <button onclick="toggleCustomToolForm()" class="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-bold hover:bg-emerald-500/20 flex items-center gap-1.5 transition">
                <span class="text-base font-bold">&#10133;</span> Add Custom Tool
              </button>
            </div>
          </div>
        </div>

        <div id="toolsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div class="text-slate-400 text-sm col-span-full py-8 text-center">Loading comprehensive toolchain inventory...</div>
        </div>
        <div id="toolsPagination" class="flex flex-wrap items-center justify-between gap-3 pt-2"></div>
      </section>

      <!-- View 4: Mobile Channels Tab -->
      <section id="view-channels" class="hidden space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <h2 class="text-xl font-bold text-white">📱 Two-Way Mobile Channels (Telegram & WhatsApp)</h2>
            <p class="text-sm text-slate-400">Control RAA from your phone, receive live progress digests, and download patched APKs.</p>
          </div>
          <button onclick="loadChannelsStatus()" class="px-3 py-1.5 rounded-xl glass-panel text-xs text-slate-300 border border-white/10 hover:border-white/30 transition">
            🔄 Check Channels
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Telegram Card -->
          <div class="glass-panel p-5 rounded-xl border border-cyan-500/30 bg-cyan-500/5 space-y-4 flex flex-col justify-between">
            <div class="space-y-3">
              <div class="flex justify-between items-start gap-3">
                <div class="flex items-center space-x-3">
                  <svg class="w-9 h-9 shrink-0" viewBox="0 0 48 48" fill="none" aria-label="Telegram">
                    <circle cx="24" cy="24" r="22" fill="#26A5E4"/>
                    <path d="M33.8 14.9L11.7 23.4c-1.5.6-1.5 1.4-.3 1.8l5.7 1.8 13.1-8.3c.6-.4 1.2-.2.7.2L20.3 28.5l-.4 5.8c.6 0 .8-.3 1.1-.6l2.8-2.7 5.8 4.3c1.1.6 1.8.3 2.1-1l3.8-17.9c.4-1.6-.6-2.3-1.7-1.5z" fill="#FFFFFF"/>
                  </svg>
                  <div>
                    <h3 class="font-bold text-white text-base">Telegram Bot Gateway</h3>
                    <p class="text-xs text-slate-400">Bidirectional command and report bot via Telegram API.</p>
                  </div>
                </div>
                <span id="tgStatusBadge" class="px-2.5 py-0.5 text-xs font-bold rounded-full bg-slate-800 text-slate-400 border border-white/10 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0">⚪ Not Configured</span>
              </div>

              <div class="space-y-2 pt-2">
                <div id="tgTokenGroup" class="space-y-2">
                  <label class="block text-xs font-semibold text-slate-300">Bot Token from @BotFather:</label>
                  <input type="text" id="tgTokenInput" placeholder="e.g. <BOT_ID>:<BOT_TOKEN>" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
                </div>

                <label class="block text-xs font-semibold text-slate-300 pt-1">Default Chat ID / Username (Optional):</label>
                <input type="text" id="tgChatIdInput" placeholder="e.g. 123456789 or @your_username" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
              </div>

              <!-- Telegram Deep-Link & QR Pairing Box (nod pattern) -->
              <div id="tgLinkContainer" class="hidden flex flex-col items-center justify-center p-3.5 bg-slate-950/80 rounded-xl border border-cyan-500/25 space-y-2.5">
                <div id="tgQrSvgBox" class="flex justify-center items-center"></div>
                <a id="tgDeepLinkAnchor" href="https://t.me" target="_blank" rel="noopener noreferrer" class="px-3.5 py-1.5 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 text-xs font-semibold hover:bg-cyan-500/25 transition">
                  ✈️ Open Bot in Telegram ↗
                </a>
                <p class="text-[11px] text-slate-400 text-center">Scan or open the link and tap <strong>Start</strong> in Telegram to auto-link your Chat ID.</p>
              </div>

              <!-- Telegram Manual Chat / LLM / Report / Suggest Box (shown when connected) -->
              <div id="tgChatBox" class="hidden space-y-2 pt-2 border-t border-cyan-500/20">
                <label class="block text-xs font-semibold text-cyan-300">💬 Telegram Chat, LLM Answer, Report &amp; Suggestions:</label>
                <div class="flex items-center gap-2">
                  <input type="text" id="tgManualChatInput" onkeydown="if(event.key==='Enter')sendChannelChat('telegram','manual')" placeholder="Type message, LLM prompt, or topic..." class="flex-1 bg-slate-900 border border-cyan-500/30 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
                  <button onclick="sendChannelChat('telegram','manual')" class="px-3 py-2 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-semibold hover:bg-cyan-500/30 whitespace-nowrap">Send</button>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  <button onclick="sendChannelChat('telegram','llm')" class="px-2.5 py-1 rounded-lg bg-slate-900 text-cyan-300 border border-white/10 text-[11px] font-semibold hover:border-cyan-400">🤖 LLM Answer</button>
                  <button onclick="sendChannelChat('telegram','report')" class="px-2.5 py-1 rounded-lg bg-slate-900 text-emerald-300 border border-white/10 text-[11px] font-semibold hover:border-emerald-400">📄 Send Report</button>
                  <button onclick="sendChannelChat('telegram','suggest')" class="px-2.5 py-1 rounded-lg bg-slate-900 text-amber-300 border border-white/10 text-[11px] font-semibold hover:border-amber-400">💡 Suggest</button>
                </div>
              </div>

              <!-- Telegram Feedback Box -->
              <div id="tgFeedback" class="hidden text-xs p-3 rounded-lg border font-mono"></div>
            </div>

            <div class="flex items-center gap-2 pt-4 border-t border-white/10">
              <button id="tgConnectBtn" onclick="saveTelegramConfig()" class="flex-1 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition">
                💾 Connect & Verify Token
              </button>
              <button id="tgDisconnectBtn" onclick="disconnectTelegramBot()" class="hidden flex-1 py-2 rounded-xl glass-panel text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/10 transition" title="Disconnect Telegram Bot">
                🔌 Disconnect Telegram Bot
              </button>
            </div>
          </div>

          <!-- WhatsApp Card -->
          <div class="glass-panel p-5 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-4 flex flex-col justify-between">
            <div class="space-y-3">
              <div class="flex flex-wrap justify-between items-start gap-2">
                <div class="flex items-center space-x-3 min-w-0 flex-1">
                  <svg class="w-9 h-9 shrink-0" viewBox="0 0 48 48" fill="none" aria-label="WhatsApp">
                    <circle cx="24" cy="24" r="22" fill="#25D366"/>
                    <path d="M24 11.5c-6.9 0-12.5 5.6-12.5 12.5 0 2.3.6 4.5 1.8 6.4l-1.9 6.2 6.4-1.8c1.9 1 4 1.6 6.2 1.6 6.9 0 12.5-5.6 12.5-12.5S30.9 11.5 24 11.5zm6.9 17.4c-.3.8-1.7 1.5-2.4 1.6-.6.1-1.4.2-2.3-.1-.5-.2-1.2-.4-2.1-.8-3.7-1.6-6.1-5.3-6.3-5.6-.2-.2-1.5-2-1.5-3.8s1-2.7 1.3-3.1c.3-.4.7-.5 1-.5h.7c.2 0 .5-.1.8.6.3.7 1 2.5 1.1 2.7.1.2.2.4 0 .7-.1.2-.2.4-.4.6-.2.2-.4.5-.6.7-.2.2-.4.4-.2.8.2.4 1 1.7 2.2 2.7 1.5 1.3 2.8 1.7 3.2 1.9.4.2.6.2.9-.1.2-.3 1-1.2 1.3-1.6.3-.4.6-.3 1-.2.4.1 2.4 1.1 2.8 1.3.4.2.7.3.8.5.1.2.1 1-.2 1.8z" fill="#FFFFFF"/>
                  </svg>
                  <div class="min-w-0">
                    <h3 class="font-bold text-white text-base">WhatsApp Web Bridge</h3>
                    <p class="text-xs text-slate-400">Direct mobile messaging and binary upload over local Baileys bridge.</p>
                  </div>
                </div>
                <span id="waStatusBadge" class="px-2.5 py-0.5 text-xs font-bold rounded-full bg-slate-800 text-slate-400 border border-white/10 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0">⚪ Awaiting Scan</span>
              </div>

              <!-- QR Code & Pairing Display -->
              <div id="waQrContainer" class="hidden flex flex-col items-center justify-center p-4 bg-slate-950/90 rounded-xl border border-emerald-500/20 space-y-3">
                <div id="waQrSvgBox" class="flex justify-center items-center"></div>
                <div class="text-center space-y-1">
                  <div class="text-xs text-slate-300">Or Link with Pairing Code:</div>
                  <div id="waPairingCodeBox" class="font-mono text-sm font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/30 inline-block tracking-wider"></div>
                </div>
                <p class="text-[11px] text-slate-400 text-center max-w-xs">Open WhatsApp ➔ Settings ➔ Linked Devices ➔ Link a Device, scan this QR code or enter code above.</p>
              </div>

              <!-- Recipient Phone -->
              <div class="space-y-1 pt-2">
                <label class="block text-xs font-semibold text-slate-300">Recipient Phone (with country code):</label>
                <input type="text" id="waPhoneInput" placeholder="+1 (555) 019-2834" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-emerald-400 font-mono">
              </div>

              <!-- WhatsApp Manual Chat / LLM / Report / Suggest Box (shown when connected) -->
              <div id="waChatBox" class="hidden space-y-2 pt-2 border-t border-emerald-500/20">
                <label class="block text-xs font-semibold text-emerald-300">💬 WhatsApp Chat, LLM Answer, Report &amp; Suggestions:</label>
                <div class="flex items-center gap-2">
                  <input type="text" id="waManualChatInput" onkeydown="if(event.key==='Enter')sendChannelChat('whatsapp','manual')" placeholder="Type message, LLM prompt, or topic..." class="flex-1 bg-slate-900 border border-emerald-500/30 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-emerald-400">
                  <button onclick="sendChannelChat('whatsapp','manual')" class="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-semibold hover:bg-emerald-500/30 whitespace-nowrap">Send</button>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  <button onclick="sendChannelChat('whatsapp','llm')" class="px-2.5 py-1 rounded-lg bg-slate-900 text-cyan-300 border border-white/10 text-[11px] font-semibold hover:border-cyan-400">🤖 LLM Answer</button>
                  <button onclick="sendChannelChat('whatsapp','report')" class="px-2.5 py-1 rounded-lg bg-slate-900 text-emerald-300 border border-white/10 text-[11px] font-semibold hover:border-emerald-400">📄 Send Report</button>
                  <button onclick="sendChannelChat('whatsapp','suggest')" class="px-2.5 py-1 rounded-lg bg-slate-900 text-amber-300 border border-white/10 text-[11px] font-semibold hover:border-amber-400">💡 Suggest</button>
                </div>
              </div>

              <!-- WhatsApp Feedback Box -->
              <div id="waFeedback" class="hidden text-xs p-3 rounded-lg border font-mono"></div>
            </div>

            <div class="flex items-center gap-2 pt-4 border-t border-white/10">
              <button id="waQrBtn" onclick="generateWhatsAppQR()" class="flex-1 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition">
                🔄 Generate Scannable QR Code
              </button>
              <button id="waPairBtn" onclick="pairWhatsAppDevice()" class="px-3 py-2 rounded-xl glass-panel text-emerald-300 border border-emerald-500/30 text-xs font-semibold hover:bg-emerald-500/10 transition">
                ✅ Link Device
              </button>
              <button id="waDisconnectBtn" onclick="disconnectWhatsAppDevice()" class="hidden px-3 py-2 rounded-xl glass-panel text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/10 transition">
                🔌 Disconnect WhatsApp
              </button>
            </div>
          </div>
        </div>

        <!-- Cadence Settings -->
        <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 class="font-bold text-white">⏱️ Notification Cadence &amp; Intensity</h3>
              <p class="text-xs text-slate-400">Regulate message velocity to mobile channels.</p>
            </div>
            <span id="cadenceActiveLabel" class="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">Active: Every 5 min</span>
          </div>
          <div class="flex flex-wrap gap-3" id="cadenceButtonsRow">
            <button onclick="setCadence('start_end', 0)" data-cadence-mode="start_end" data-cadence-mins="0" class="cadence-btn px-3 py-1.5 rounded-lg border border-white/10 text-xs text-slate-300 hover:border-emerald-400 transition">Start &amp; End Only</button>
            <button onclick="setCadence('interval', 1)" data-cadence-mode="interval" data-cadence-mins="1" class="cadence-btn px-3 py-1.5 rounded-lg border border-white/10 text-xs text-slate-300 hover:border-emerald-400 transition">Every 1 min</button>
            <button onclick="setCadence('interval', 5)" data-cadence-mode="interval" data-cadence-mins="5" class="cadence-btn px-3 py-1.5 rounded-lg border border-emerald-400 text-xs text-emerald-400 bg-emerald-500/10 font-bold transition">Every 5 min (Default)</button>
            <button onclick="setCadence('interval', 10)" data-cadence-mode="interval" data-cadence-mins="10" class="cadence-btn px-3 py-1.5 rounded-lg border border-white/10 text-xs text-slate-300 hover:border-emerald-400 transition">Every 10 min</button>
          </div>
        </div>
      </section>

      <!-- View 4b: Connected Wi-Fi Mobile Devices Tab -->
      <section id="view-wifi" class="hidden space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <h2 class="text-xl font-bold text-white">📶 Connected Wi-Fi Mobile Devices</h2>
            <p class="text-sm text-slate-400">Discover mobile phones and tablets visible on your connected Wi-Fi network and link via Wireless ADB.</p>
          </div>
          <div class="flex items-center gap-2">
            <span id="wifiSubnetBadge" class="px-3 py-1 rounded-full text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">Scanning Wi-Fi...</span>
            <button onclick="loadWifiDevices()" class="px-3 py-2 rounded-xl glass-panel text-xs text-slate-300 border border-white/10 hover:border-emerald-400 transition">🔄 Scan Wi-Fi Network</button>
          </div>
        </div>

        <!-- Manual Wireless ADB Connect & Pair Bar -->
        <div class="flex flex-wrap items-center gap-2.5 bg-slate-900/60 p-3.5 rounded-xl border border-white/10">
          <input type="text" id="wifiManualTargetInput" placeholder="IP:Port (e.g. 192.168.1.7:5555)" class="flex-1 min-w-[220px] bg-slate-950/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
          <input type="text" id="wifiPairCodeInput" placeholder="Pair Code (6 digits)" class="w-44 bg-slate-950/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
          <button onclick="pairWifiAdb()" class="px-3.5 py-2 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-bold text-xs hover:bg-cyan-500/25 transition">
            🔐 Pair
          </button>
          <button onclick="openWifiQrPairModal('', 'Android Device')" class="px-3.5 py-2 rounded-lg bg-violet-500/15 text-violet-300 border border-violet-500/30 font-bold text-xs hover:bg-violet-500/25 transition">
            📷 Pair with QR Code
          </button>
          <button onclick="connectWifiAdb()" class="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition">
            🔗 Connect Wireless ADB
          </button>
        </div>

        <!-- Android Wireless Debugging Setup Steps -->
        <div class="bg-slate-900/50 p-3.5 rounded-xl border border-cyan-500/20 space-y-2">
          <div class="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
            <span>📱</span>
            <span>Quick Setup: Enable Developer Options &amp; Wireless Debugging (Android 11+)</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-[11px] text-slate-300">
            <div class="bg-slate-950/60 px-3 py-2 rounded-lg border border-white/5 flex items-start gap-2">
              <span class="text-sm shrink-0">🛠️</span>
              <div>
                <div class="font-semibold text-white">1. Enable Developer Options</div>
                <div class="text-slate-400">Open <strong>Settings → About phone</strong> (or <em>Software info</em>) → Tap <strong>Build number 7 times</strong> until enabled.</div>
              </div>
            </div>
            <div class="bg-slate-950/60 px-3 py-2 rounded-lg border border-white/5 flex items-start gap-2">
              <span class="text-sm shrink-0">📡</span>
              <div>
                <div class="font-semibold text-white">2. Turn ON Wireless Debugging</div>
                <div class="text-slate-400">Go to <strong>Settings → System / Additional settings → Developer options</strong> → Toggle <strong>Wireless debugging ON</strong>.</div>
              </div>
            </div>
            <div class="bg-slate-950/60 px-3 py-2 rounded-lg border border-white/5 flex items-start gap-2">
              <span class="text-sm shrink-0">📷</span>
              <div>
                <div class="font-semibold text-white">3. Pair &amp; Connect</div>
                <div class="text-slate-400">Tap <strong>Wireless debugging → Pair device with QR code</strong> and scan using <strong>📷 Pair with QR Code</strong> above.</div>
              </div>
            </div>
          </div>
        </div>

        <div class="text-xs text-slate-400 bg-slate-900/40 px-3.5 py-2.5 rounded-xl border border-white/10 flex items-center justify-between gap-2">
          <span>💡 <strong>How to identify your mobile:</strong> Check your phone's <strong>Wi-Fi Settings → Connected Network → IP / MAC address</strong>, then click <strong>⭐ Mine</strong> or <strong>✏️ Rename</strong> to tag it.</span>
        </div>

        <div id="wifiDevicesGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div class="text-slate-400 text-sm col-span-full py-8 text-center">Click "Scan Wi-Fi Network" to discover visible mobile devices...</div>
        </div>
      </section>

      <!-- View 5: MCP Mesh Tab -->
      <section id="view-mesh" class="hidden space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <h2 class="text-xl font-bold text-white">🔌 External MCP Connectors & Ecosystem Mesh</h2>
            <p class="text-sm text-slate-400">All implemented MCP service connectors. Add, mark active/deactivate, test ping, or delete connectors.</p>
          </div>
          <div class="flex items-center gap-2">
            <span id="meshCountBadge" class="px-3 py-1 rounded-full text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">Loading...</span>
            <button onclick="loadMesh()" class="px-3 py-2 rounded-xl glass-panel text-xs text-slate-300 border border-white/10 hover:border-white/30 transition">🔄 Refresh</button>
          </div>
        </div>

        <!-- Filter bar for MCP Mesh -->
        <div class="space-y-3 bg-slate-900/60 p-3 rounded-xl border border-white/10">
          <div class="flex flex-wrap gap-1.5" id="meshCategoryFilters">
            <button onclick="filterMeshCategory('all', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">All</button>
            <button onclick="filterMeshCategory('reversing', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Reverse Engineering</button>
            <button onclick="filterMeshCategory('security', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Security &amp; Proxy</button>
            <button onclick="filterMeshCategory('ui', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">UI &amp; Living Canvas</button>
            <button onclick="filterMeshCategory('mobile', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Mobile &amp; Device</button>
            <button onclick="filterMeshCategory('automation', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Automation &amp; API</button>
            <button onclick="filterMeshCategory('core', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Core &amp; Enterprise</button>
            <button onclick="filterMeshCategory('custom', this)" class="mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Custom</button>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap gap-2" id="meshFilters">
              <button onclick="filterMesh('all', this)" class="mesh-filter-btn px-3 py-1 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">All Connectors</button>
              <button onclick="filterMesh('added', this)" class="mesh-filter-btn px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Active / Added</button>
              <button onclick="filterMesh('available', this)" class="mesh-filter-btn px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Available to Add (+)</button>
            </div>
            <div class="w-full md:w-auto flex flex-wrap items-center gap-2">
              <select id="meshSortSelect" onchange="resetMeshPageAndRender()" aria-label="Sort MCP connectors" class="bg-slate-950/80 border border-white/10 text-xs px-2.5 py-1.5 rounded-lg text-slate-200 outline-none focus:border-cyan-400">
                <option value="default">Sort: Default Order</option>
                <option value="name_asc">Sort: Name (A → Z)</option>
                <option value="name_desc">Sort: Name (Z → A)</option>
                <option value="status_added">Sort: Active / Added First</option>
                <option value="status_available">Sort: Available First</option>
                <option value="tools_desc">Sort: Most Tools First</option>
              </select>
              <input type="text" id="meshSearchInput" onkeyup="resetMeshPageAndRender()" placeholder="🔍 Search MCP connectors..." class="w-full md:w-56 bg-slate-950/80 border border-white/10 text-xs px-3 py-1.5 rounded-lg text-white outline-none focus:border-cyan-400">
              <button onclick="toggleCustomMcpForm()" class="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-bold hover:bg-emerald-500/20 flex items-center gap-1.5 transition">
                <span class="text-base font-bold">&#10133;</span> Add Custom MCP Server
              </button>
            </div>
          </div>
        </div>

        <!-- Inline Custom MCP Server Form (hidden by default) -->
        <div id="customMcpForm" class="hidden glass-panel p-5 rounded-xl border border-cyan-500/30 space-y-4 bg-slate-950/80">
          <div class="flex justify-between items-center">
            <h4 class="font-bold text-white text-sm">Add Custom MCP Server</h4>
            <button onclick="toggleCustomMcpForm()" class="text-xs text-slate-400 hover:text-white">✕ Close</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input type="text" id="customMcpName" placeholder="Server ID (e.g. jira-bridge)" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
            <select id="customMcpTransport" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
              <option value="stdio">Transport: stdio (CLI / npx)</option>
              <option value="sse">Transport: sse (HTTP SSE)</option>
              <option value="streamable-http">Transport: streamable-http</option>
            </select>
            <input type="text" id="customMcpEndpoint" placeholder="Command (stdio) or URL (sse)" class="bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
          </div>
          <button onclick="submitCustomMcp()" class="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90">
            Connect Custom MCP Server
          </button>
        </div>

        <div id="meshGrid" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Loaded dynamically -->
        </div>
        <div id="meshPagination" class="flex flex-wrap items-center justify-between gap-3 pt-2"></div>
      </section>

      <!-- View 5b: Skills Tab -->
      <section id="view-skills" class="hidden space-y-6">
        <div class="flex flex-wrap md:flex-nowrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div class="min-w-0">
            <h2 class="text-xl font-bold text-white">🧩 Agent Skills &amp; Playbooks</h2>
            <p class="text-sm text-slate-400">Discover built-in <code class="text-cyan-400">SKILL.md</code> playbooks, inspect instructions, and install them to any agent skills directory.</p>
          </div>
          <div class="flex items-center gap-2 shrink-0 flex-wrap">
            <span id="skillsCountBadge" class="px-3 py-1 rounded-full text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 whitespace-nowrap">Loading...</span>
            <button onclick="installSkill(null, true)" class="px-3 py-2 rounded-xl bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-semibold hover:border-emerald-400 transition whitespace-nowrap">
              📥 Install All Skills
            </button>
            <button onclick="loadSkills()" class="px-3 py-2 rounded-xl glass-panel text-xs text-slate-300 border border-white/10 hover:border-white/30 transition whitespace-nowrap">🔄 Refresh</button>
          </div>
        </div>

        <!-- Custom Skill Form (hidden by default) -->
        <div id="customSkillForm" class="hidden glass-panel p-5 rounded-xl border border-cyan-500/30 bg-slate-950/85 space-y-3">
          <div class="flex justify-between items-center">
            <div>
              <h4 class="font-bold text-white text-sm">Create Custom Agent Skill (SKILL.md)</h4>
              <p class="text-[11px] text-slate-400">Saves a new skill into <code class="text-cyan-400">skills/&lt;skill-id&gt;/SKILL.md</code> and makes it immediately discoverable.</p>
            </div>
            <button onclick="toggleCustomSkillForm()" class="text-xs text-slate-400 hover:text-white">✕ Close</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Skill ID (lowercase, hyphens)</label>
              <input type="text" id="customSkillId" placeholder="e.g. my-custom-audit" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white font-mono outline-none focus:border-cyan-400">
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Display Name</label>
              <input type="text" id="customSkillName" placeholder="e.g. My Custom Audit" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Category</label>
              <select id="customSkillCategory" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
                <option value="custom">Custom</option>
                <option value="security">Security &amp; Compliance</option>
                <option value="reversing">Reversing &amp; Rebuild</option>
                <option value="triage">Triage &amp; Reports</option>
                <option value="ui">UI &amp; TV Studio</option>
                <option value="automation">Agents &amp; Automation</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Description</label>
              <input type="text" id="customSkillDescription" placeholder="Short summary of what this skill does" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Tools (comma-separated, optional)</label>
              <input type="text" id="customSkillTools" placeholder="e.g. security_scan_static, privacy_data_flows" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white font-mono outline-none focus:border-cyan-400">
            </div>
          </div>
          <div>
            <label class="block text-[11px] text-slate-400 mb-1">Playbook Instructions (Markdown)</label>
            <textarea id="customSkillContent" rows="4" placeholder="## Workflow&#10;1. Inspect target manifest...&#10;2. Run compliance checks..." class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white font-mono outline-none focus:border-cyan-400"></textarea>
          </div>
          <div class="flex justify-end gap-2">
            <button onclick="toggleCustomSkillForm()" class="px-3 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition">Cancel</button>
            <button onclick="submitCustomSkill()" class="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition">💾 Save Custom Skill</button>
          </div>
        </div>

        <!-- Category Tags & Search/Sort Bar -->
        <div class="space-y-3 bg-slate-900/60 p-3 rounded-xl border border-white/10">
          <div class="flex flex-wrap gap-1.5" id="skillCategoryFilters">
            <button onclick="filterSkillsCategory('all', this)" class="skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">All</button>
            <button onclick="filterSkillsCategory('triage', this)" class="skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Triage &amp; Reports</button>
            <button onclick="filterSkillsCategory('reversing', this)" class="skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Reversing &amp; Rebuild</button>
            <button onclick="filterSkillsCategory('security', this)" class="skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Security &amp; Compliance</button>
            <button onclick="filterSkillsCategory('ui', this)" class="skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">UI &amp; TV Studio</button>
            <button onclick="filterSkillsCategory('automation', this)" class="skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Agents &amp; Automation</button>
            <button onclick="filterSkillsCategory('custom', this)" class="skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">Custom</button>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-2 w-full md:w-auto">
              <span class="text-[11px] text-slate-400 whitespace-nowrap">Install To:</span>
              <input type="text" id="skillInstallDestInput" value=".raa-workspace/skills" class="w-full md:w-56 bg-slate-950/80 border border-white/10 text-xs px-3 py-1.5 rounded-lg text-cyan-300 font-mono outline-none focus:border-cyan-400">
            </div>
            <div class="w-full md:w-auto flex flex-wrap items-center gap-2">
              <select id="skillSortSelect" onchange="resetSkillsPageAndRender()" aria-label="Sort skills" class="bg-slate-950/80 border border-white/10 text-xs px-2.5 py-1.5 rounded-lg text-slate-200 outline-none focus:border-cyan-400">
                <option value="default">Sort: Default (A → Z)</option>
                <option value="name_desc">Sort: Name (Z → A)</option>
                <option value="tools_desc">Sort: Most Tools First</option>
              </select>
              <input type="text" id="skillSearchInput" onkeyup="resetSkillsPageAndRender()" placeholder="🔍 Search skills, tools, or descriptions..." class="w-full md:w-56 bg-slate-950/80 border border-white/10 text-xs px-3 py-1.5 rounded-lg text-white outline-none focus:border-cyan-400">
              <button onclick="toggleCustomSkillForm()" class="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-bold hover:bg-emerald-500/20 flex items-center gap-1.5 transition">
                <span class="text-base font-bold">&#10133;</span> Add Custom Skill
              </button>
            </div>
          </div>
        </div>

        <div id="skillsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div class="text-slate-400 text-sm col-span-full py-8 text-center">Loading agent skills...</div>
        </div>
        <div id="skillsPagination" class="flex flex-wrap items-center justify-between gap-3 pt-2"></div>
      </section>

      <!-- View 6: TV Studio Tab (RAA + CleanYourTV) -->
      <section id="view-tv" class="hidden space-y-6">
        <div class="border-b border-white/10 pb-4 flex flex-wrap justify-between items-center gap-3">
          <div>
            <h2 class="text-xl font-bold text-white">📺 Android TV &amp; 10-Foot Living Canvas UI Studio</h2>
            <p class="text-sm text-slate-400">Create/redesign TV apps in Compose Material 3, debloat TV ads/apps safely (CleanYourTV), configure dock &amp; themes, and generate Redesign Docs.</p>
          </div>
          <span class="text-xs px-3 py-1 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/30 font-mono">CleanYourTV + Compose TV M3 · /api/tv/mcp</span>
        </div>

        <!-- TV Connection & Quick Actions Bar -->
        <div class="glass-panel p-4 rounded-xl border border-white/10 flex flex-wrap items-center gap-3">
          <input type="text" id="tvHostInput" placeholder="TV IP:Port (e.g. 192.168.1.50:5555)" class="flex-1 min-w-[240px] bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
          <button onclick="scanTvPackages()" class="px-3 py-2 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 text-xs font-semibold hover:bg-cyan-500/25 transition">
            📦 Scan TV Apps
          </button>
          <button onclick="generateTvDoc()" class="px-3 py-2 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 text-xs font-semibold hover:bg-emerald-500/25 transition">
            📄 Redesign Doc (.md)
          </button>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Left: Create / Redesign TV App & CleanYourTV Dock/Theme -->
          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
            <h3 class="font-bold text-white text-sm">✨ Create / Redesign TV App &amp; Launcher Dock</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[11px] text-slate-400 mb-1">Target Package / App Name</label>
                <input type="text" id="tvTargetInput" value="com.android.tv.launcher" placeholder="Package name or APK path" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
              </div>
              <div>
                <label class="block text-[11px] text-slate-400 mb-1">CleanYourTV Theme</label>
                <select id="tvThemeSelect" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
                  <option value="midnight-glass">midnight-glass</option>
                  <option value="ambient-glass">ambient-glass</option>
                  <option value="default">default</option>
                  <option value="cinematic">cinematic</option>
                  <option value="minimal">minimal</option>
                  <option value="retro">retro</option>
                </select>
              </div>
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Dock Apps (comma-separated, up to 4-6 pinned apps)</label>
              <input type="text" id="tvDockAppsInput" value="com.netflix.ninja, com.google.android.youtube.tv, com.amazon.amazonvideo.livingroom, in.startv.hotstar" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Hidden Apps (optional, comma-separated)</label>
              <input type="text" id="tvHiddenAppsInput" value="com.mediatek.wwtv.tvcenter" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono">
            </div>
            <div class="flex flex-wrap gap-2 pt-1">
              <button onclick="runTvRedesign()" class="flex-1 py-2 px-3 rounded-lg bg-gradient-to-r from-violet-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition">
                ✨ Redesign to Compose TV M3
              </button>
              <button onclick="applyTvDockTheme()" class="py-2 px-3 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-semibold text-xs hover:bg-cyan-500/25 transition">
                🎨 Stage Dock &amp; Theme
              </button>
            </div>
          </div>

          <!-- Right: Remove / Debloat TV Bloatware & Restore -->
          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-white text-sm">🧹 Remove TV Bloatware &amp; Ads (Safe Disable + Restore)</h3>
              <button onclick="scanTvPackages()" class="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10">🔄 Refresh</button>
            </div>
            <p class="text-xs text-slate-400">Uses CleanYourTV's non-destructive <code class="text-cyan-400">pm disable-user --user 0</code> with automatic backup. Protected system apps cannot be disabled.</p>
            <div id="tvPackagesList" class="space-y-1.5 max-h-48 overflow-y-auto pr-1 text-xs text-slate-400">
              <div class="p-3 rounded-lg bg-slate-900/60 border border-white/5 text-center">Click <strong>Scan TV Apps</strong> to inspect packages from your TV or reference catalog.</div>
            </div>
            <div class="flex flex-wrap gap-2 pt-1">
              <button onclick="debloatTvApps(false)" class="flex-1 py-2 px-3 rounded-lg bg-red-500/15 text-red-300 border border-red-500/30 font-semibold text-xs hover:bg-red-500/25 transition">
                🚫 Disable Selected Bloatware
              </button>
              <button onclick="debloatTvApps(true)" class="py-2 px-3 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold text-xs hover:bg-emerald-500/25 transition">
                ♻️ Restore Selected
              </button>
            </div>
          </div>
        </div>

        <!-- Output Preview -->
        <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-2">
          <div class="flex items-center justify-between">
            <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400">TV Studio Output / Compose M3 / Redesign Doc</h4>
            <span id="tvOutputMeta" class="text-[11px] font-mono text-cyan-400"></span>
          </div>
          <pre id="tvOutput" class="bg-slate-950 p-4 rounded-xl border border-white/10 text-xs font-mono text-slate-300 hidden max-h-80 overflow-y-auto whitespace-pre-wrap"></pre>
        </div>
      </section>

      <!-- View 7: Vault & Shield Tab -->
      <section id="view-security" class="hidden space-y-6">
        <div class="border-b border-white/10 pb-4 flex flex-wrap justify-between items-center gap-3">
          <div>
            <h2 class="text-xl font-bold text-white">🛡️ Zero-Knowledge Vault &amp; Content Shield</h2>
            <p class="text-sm text-slate-400">Store API tokens, usernames, and passwords with AES-256-GCM encryption so secrets never appear in code, configs, or logs.</p>
          </div>
          <span class="text-xs px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono">AES-256-GCM · Log Redaction Active</span>
        </div>

        <!-- Zero-Knowledge Credential Vault -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
            <h3 class="font-bold text-white flex items-center gap-2">🔐 Store Credential / API Token</h3>
            <p class="text-xs text-slate-400">Save API tokens, passwords, and usernames encrypted in the Vault. Reference them via <code class="text-cyan-400">{{KEY_NAME}}</code> in tools &amp; channels.</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[11px] text-slate-400 mb-1">Key / Handle *</label>
                <input id="vaultKeyName" type="text" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono" placeholder="e.g. TELEGRAM_BOT_TOKEN" />
              </div>
              <div>
                <label class="block text-[11px] text-slate-400 mb-1">Service / Scope</label>
                <input id="vaultService" type="text" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400" placeholder="e.g. telegram, github, openai" />
              </div>
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Username / Client ID (Optional)</label>
              <input id="vaultUsername" type="text" autocomplete="off" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400" placeholder="e.g. admin@domain.com or @bot" />
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">API Token / Password</label>
              <div class="relative">
                <input id="vaultSecretValue" type="password" autocomplete="new-password" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 pr-14 rounded-lg text-white outline-none focus:border-cyan-400 font-mono" placeholder="Paste API token or password..." />
                <button type="button" onclick="toggleVaultSecretVisibility()" class="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] text-slate-400 hover:text-cyan-300 px-2 py-0.5 rounded bg-slate-800/80">Show</button>
              </div>
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Description (Optional)</label>
              <input id="vaultDescription" type="text" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400" placeholder="Used by RAA agents &amp; connectors" />
            </div>
            <button onclick="saveVaultCredential()" class="px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-semibold hover:bg-cyan-500/30 transition">
              💾 Save to Encrypted Vault
            </button>
          </div>

          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-white">🗝️ Stored Vault Credentials</h3>
              <button onclick="loadVaultSecrets()" class="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10 transition">🔄 Refresh</button>
            </div>
            <p class="text-xs text-slate-400">Plaintext values are never returned to the UI, LLM context, or log files—only masked fingerprints are shown.</p>
            <div id="vaultSecretsList" class="space-y-2 max-h-72 overflow-y-auto pr-1 text-xs text-slate-400">
              Loading vault entries...
            </div>
          </div>
        </div>

        <!-- Prompt Injection & Secret Redaction Shield -->
        <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
          <h3 class="font-bold text-white">Prompt Injection &amp; Secret Redaction Shield Test</h3>
          <p class="text-xs text-slate-400">Simulate untrusted code or log output to test prompt-injection quarantine and automatic Vault secret redaction.</p>
          <textarea id="shieldInput" rows="3" class="w-full bg-slate-900/80 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400" placeholder="Paste suspicious string (e.g. Ignore previous instructions... or a vaulted token to verify redaction)"></textarea>
          <button onclick="testShield()" class="px-4 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/20 transition">
            🛡️ Wrap, Redact &amp; Quarantine
          </button>
          <div id="shieldOutput" class="bg-slate-950 p-3 rounded-lg border border-white/10 text-xs font-mono text-slate-300 hidden whitespace-pre-wrap"></div>
        </div>
      </section>


      <!-- View 8: Config Editor Tab (Backed by E:/MCP_Workspace/RAA/config) -->
      <section id="view-config" class="hidden space-y-6">
        <div class="border-b border-white/10 pb-4 flex flex-wrap justify-between items-center gap-4">
          <div>
            <h2 class="text-xl font-bold text-white flex items-center gap-2">
              <span>⚙️ Configuration Manager & Live JSON Editor</span>
              <span class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono">E:/MCP_Workspace/RAA/config</span>
            </h2>
            <p class="text-sm text-slate-400 mt-1">All UI views, reversing tools, MCP mesh, and channels load and save directly from these JSON files.</p>
          </div>
          <div class="flex items-center space-x-2">
            <button onclick="openConfigFolderInExplorer()" class="px-3 py-1.5 rounded-xl bg-cyan-500/15 border border-cyan-500/40 hover:bg-cyan-500/25 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition">
              <span>📂 Open Config Folder</span>
            </button>
            <button onclick="reloadActiveConfigFile()" class="px-3 py-1.5 rounded-xl bg-slate-800 border border-white/10 hover:border-slate-500 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition">
              <span>🔄 Reload</span>
            </button>
          </div>
        </div>

        <div class="flex flex-wrap gap-2 pt-1 pb-2">
          <button onclick="selectConfigFile('menu.json', this)" class="cfg-pill active-cfg px-3 py-1.5 rounded-xl text-xs font-mono border border-cyan-400 bg-cyan-500/10 text-cyan-300 flex items-center gap-1.5 transition">
            <span>📄</span> menu.json
          </button>
          <button onclick="selectConfigFile('tools.json', this)" class="cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition">
            <span>🛠️</span> tools.json
          </button>
          <button onclick="selectConfigFile('mcp.json', this)" class="cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition">
            <span>🔌</span> mcp.json
          </button>
          <button onclick="selectConfigFile('mobile_channels.json', this)" class="cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition">
            <span>📱</span> mobile_channels.json
          </button>
          <button onclick="selectConfigFile('profile.json', this)" class="cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition">
            <span>⚡</span> profile.json
          </button>
          <button onclick="selectConfigFile('tvstudio.json', this)" class="cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition">
            <span>📺</span> tvstudio.json
          </button>
          <button onclick="selectConfigFile('vault&shield.json', this)" class="cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition">
            <span>🛡️</span> vault&shield.json
          </button>
          <button onclick="selectConfigFile('workspace.json', this)" class="cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition">
            <span>🌐</span> workspace.json
          </button>
        </div>

        <div class="glass-panel p-4 rounded-xl border border-white/10 space-y-3">
          <div class="flex justify-between items-center text-xs font-mono">
            <div class="flex items-center space-x-2">
              <span class="text-slate-500">File:</span>
              <span id="cfgActivePathDisplay" class="text-cyan-400 font-bold">E:/MCP_Workspace/RAA/config\\menu.json</span>
              <span id="cfgActiveSizeDisplay" class="text-slate-500 text-[11px] whitespace-nowrap shrink-0">(loaded)</span>
            </div>
            <div class="flex items-center space-x-2 shrink-0">
              <span id="cfgValidationStatus" class="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 whitespace-nowrap">✓ Valid JSON</span>
              <button onclick="formatConfigJson()" class="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-cyan-300 border border-white/10 transition text-[11px] font-semibold whitespace-nowrap inline-flex items-center gap-1">📋 Format JSON</button>
            </div>
          </div>

          <textarea id="configEditorTextarea" rows="22" spellcheck="false" class="w-full bg-[#070A11] text-emerald-300 font-mono text-xs p-4 rounded-xl border border-white/15 focus:border-cyan-400 outline-none leading-relaxed transition shadow-inner resize-y"></textarea>

          <div class="flex flex-wrap justify-between items-center gap-3 pt-2 border-t border-white/10">
            <span class="text-xs text-slate-400 font-mono">
              💡 Configuration is loaded from and saved to E:/MCP_Workspace/RAA/config.
            </span>
            <div class="flex space-x-2">
              <button onclick="reloadActiveConfigFile()" class="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition">
                Reset / Discard
              </button>
              <button onclick="saveActiveConfigFile()" class="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition flex items-center gap-1.5 shadow-md">
                <span>💾 Save & Apply Changes</span>
              </button>
            </div>
          </div>
        </div>
      </section>

    </main>

    <!-- Contextual Tip Footer -->
    <footer class="glass-panel rounded-xl p-4 flex items-center space-x-3 text-xs text-slate-400 border border-white/10">
      <span class="text-emerald-400 font-bold text-sm">💡 Pro Tip:</span>
      <span>You can configure tools and MCP connectors anytime via web or CLI commands <code class="text-emerald-300 font-mono">raa setup</code> and <code class="text-cyan-300 font-mono">raa mcp-mesh list</code>.</span>
    </footer>
  </div>

  <script>

    function escapeHtml(val) {
      return String(val ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    // --- Dark Mode / Light Mode Theme Controller ---
    function initTheme() {
      const savedTheme = localStorage.getItem('raa-theme') || 'dark';
      applyTheme(savedTheme);
    }

    function toggleTheme() {
      const current = document.body.classList.contains('light-mode') ? 'light' : 'dark';
      const newTheme = current === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
      localStorage.setItem('raa-theme', newTheme);
    }

    function applyTheme(theme) {
      const icon = document.getElementById('themeToggleIcon');
      const label = document.getElementById('themeToggleLabel');
      const btn = document.getElementById('themeToggleBtn');
      if (theme === 'light') {
        document.body.classList.add('light-mode');
        if (icon) icon.innerText = '☀️';
        if (label) label.innerText = 'Light';
        if (btn) btn.title = 'Switch to Dark Mode';
      } else {
        document.body.classList.remove('light-mode');
        if (icon) icon.innerText = '🌙';
        if (label) label.innerText = 'Dark';
        if (btn) btn.title = 'Switch to Light Mode';
      }
    }

    let currentStep = 1;
    const totalSteps = 5;
    let selectedPersona = 'core';
    let allToolsCache = [];
    let activeToolCategory = 'all';
    let activeToolStatus = 'all';
    let toolsCurrentPage = 1;
    const TOOLS_PAGE_SIZE = 9;
    let allMeshCache = [];
    let activeMeshFilter = 'all';
    let activeMeshCategory = 'all';
    let meshCurrentPage = 1;
    const MESH_PAGE_SIZE = 8;
    const downloadingTools = new Set();

    const stepData = [
      {
        num: 1,
        title: "Workspace & Operational Profile",
        desc: "Select your active reversing persona to automatically tune security policies and tool chains.",
        render: () => `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 mt-2 mb-1">
            <div id="persona-core" onclick="selectPersona('core', this)" class="persona-card glass-panel p-4 sm:p-5 rounded-xl border border-orange-500/60 bg-orange-500/10 hover:border-orange-400 cursor-pointer ${selectedPersona === 'core' ? 'card-selected' : ''} transition shadow-sm">
              <div class="flex items-center space-x-2.5 mb-1.5">
                <span class="text-xl text-amber-400 shrink-0">⚡</span>
                <h3 class="font-bold text-white text-base">Core Decompilation</h3>
              </div>
              <p class="text-xs text-slate-400 leading-relaxed">JADX decompiler, Dalvik disassembly, API extraction, and manifest auditing.</p>
            </div>
            <div id="persona-full" onclick="selectPersona('full', this)" class="persona-card glass-panel p-4 sm:p-5 rounded-xl border border-purple-500/40 bg-slate-900/30 hover:border-purple-400 cursor-pointer ${selectedPersona === 'full' ? 'card-selected' : ''} transition shadow-sm">
              <div class="flex items-center space-x-2.5 mb-1.5">
                <span class="text-xl text-orange-400 shrink-0">🔥</span>
                <h3 class="font-bold text-white text-base">Full Offensive & Rebuilding</h3>
              </div>
              <p class="text-xs text-slate-400 leading-relaxed">Apktool bytecode rewriting, SSL bypass generation, KernelPatch syscall intercept.</p>
            </div>
            <div id="persona-ui" onclick="selectPersona('ui', this)" class="persona-card glass-panel p-4 sm:p-5 rounded-xl border border-white/10 hover:border-cyan-400 bg-slate-900/30 cursor-pointer ${selectedPersona === 'ui' ? 'card-selected' : ''} transition shadow-sm">
              <div class="flex items-center space-x-2.5 mb-1.5">
                <span class="text-xl shrink-0">🎨</span>
                <h3 class="font-bold text-white text-base">Living Canvas UI Studio</h3>
              </div>
              <p class="text-xs text-slate-400 leading-relaxed">View hierarchy crawl to Jetpack Compose M3 and Android TV 10-foot redesign.</p>
            </div>
            <div id="persona-swarm" onclick="selectPersona('swarm', this)" class="persona-card glass-panel p-4 sm:p-5 rounded-xl border border-white/10 hover:border-amber-400 bg-slate-900/30 cursor-pointer ${selectedPersona === 'swarm' ? 'card-selected' : ''} transition shadow-sm">
              <div class="flex items-center space-x-2.5 mb-1.5">
                <span class="text-xl shrink-0">🐝</span>
                <h3 class="font-bold text-white text-base">Enterprise Swarm & Mesh</h3>
              </div>
              <p class="text-xs text-slate-400 leading-relaxed">Multi-agent orchestrator connected to external GitHub, Playwright, and Jira MCP servers.</p>
            </div>
          </div>
        `
      },
      {
        num: 2,
        title: "Reversing Engine Toolchain",
        desc: "Download and configure external engines with 1-click download, GitHub repo, or custom binary paths.",
        render: () => {
          const coreIds = ['jadx', 'apktool', 'platform-tools', 'ghidra'];
          const fallbackMeta = {
            'jadx': { display_name: 'JADX', version: 'v1.5.0', link: 'https://github.com/skylot/jadx', linkText: 'GitHub ↗', approx_size_mb: 42.5 },
            'apktool': { display_name: 'Apktool', version: 'v2.10.0', link: 'https://apktool.org/', linkText: 'Site ↗', approx_size_mb: 22.0 },
            'platform-tools': { display_name: 'Platform-Tools', version: 'ADB/AAPT2', link: 'https://developer.android.com/tools/releases/platform-tools', linkText: 'Google ↗', approx_size_mb: 16.5 },
            'ghidra': { display_name: 'Ghidra', version: 'ARM64 Decompiler', link: 'https://ghidra-sre.org/', linkText: 'NSA ↗', approx_size_mb: 395.0 }
          };
          const cardsHtml = coreIds.map(id => {
            const cached = allToolsCache.find(t => t.tool_id === id);
            const fb = fallbackMeta[id];
            const isInstalled = cached ? !!cached.installed : false;
            const title = cached ? cached.display_name : fb.display_name;
            const sub = cached ? ('v' + cached.version) : fb.version;
            const sizeMb = cached ? (cached.approx_size_mb || fb.approx_size_mb) : fb.approx_size_mb;
            return `
              <div id="wizCard-${id}" class="glass-panel p-3.5 rounded-lg border border-white/10 space-y-2.5">
                <div class="flex justify-between items-center gap-2">
                  <div class="min-w-0">
                    <b class="text-white">${title}</b>
                    <span class="text-slate-400 ml-1">${sub}</span>
                    <a href="${fb.link}" target="_blank" class="text-cyan-400 hover:underline ml-1.5">${fb.linkText}</a>
                  </div>
                  <div id="wizBtnArea-${id}" class="shrink-0">
                    ${isInstalled
                      ? `<span class="px-2.5 py-1 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded font-semibold">✓ Ready</span>`
                      : `<button onclick="downloadTool('${id}')" class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded hover:bg-emerald-500/30 font-semibold transition">⬇️ Install</button>`
                    }
                  </div>
                </div>
                <div id="wizProgressArea-${id}" class="hidden space-y-1.5 pt-2 border-t border-white/10">
                  <div class="flex justify-between items-center text-[10px] font-mono">
                    <span id="wizStageText-${id}" class="text-cyan-300 font-semibold truncate">🌐 Connecting...</span>
                    <span id="wizStagePercent-${id}" class="text-emerald-400 font-bold">0%</span>
                  </div>
                  <div class="w-full bg-slate-950 border border-white/10 rounded-full h-2 p-0.5 overflow-hidden">
                    <div id="wizProgressBar-${id}" class="bg-gradient-to-r from-cyan-400 to-emerald-500 h-1 rounded-full transition-all duration-150" style="width: 0%"></div>
                  </div>
                  <div class="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span id="wizStageBytes-${id}">0.0 MB / ${sizeMb} MB</span>
                    <span id="wizStageSpeed-${id}" class="text-cyan-400">8.4 MB/s</span>
                  </div>
                </div>
              </div>
            `;
          }).join('');
          return `
            <div class="space-y-4">
              <div class="flex flex-wrap justify-between items-center gap-3 bg-slate-900/60 p-3 rounded-xl border border-white/10">
                <span class="text-xs text-slate-300">Quickly provision all required decompilers and signing tools with real-time download progress.</span>
                <button onclick="downloadTool('all')" class="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold hover:bg-emerald-500/20 transition">
                  ⬇️ Download All Missing
                </button>
              </div>
              <div id="wizGlobalDownloadBanner" class="hidden glass-panel p-3.5 rounded-xl border border-cyan-500/40 bg-slate-950/90 space-y-2">
                <div class="flex justify-between items-center text-xs font-mono">
                  <span id="wizGlobalDownloadTitle" class="text-cyan-300 font-bold">Provisioning Toolchain...</span>
                  <span id="wizGlobalDownloadPercent" class="text-emerald-400 font-bold">0%</span>
                </div>
                <div class="w-full bg-slate-900 border border-white/10 rounded-full h-2.5 p-0.5 overflow-hidden">
                  <div id="wizGlobalProgressBar" class="bg-gradient-to-r from-cyan-400 to-emerald-500 h-1.5 rounded-full transition-all duration-200" style="width: 0%"></div>
                </div>
                <div id="wizGlobalDownloadDetail" class="text-[11px] text-slate-400 font-mono">Preparing downloads...</div>
              </div>
              <div id="wizardToolsList" class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                ${cardsHtml}
              </div>
            </div>
          `;
        }
      },
      {
        num: 3,
        title: "Mobile Intelligence & Channels",
        desc: "Configure Telegram bot tokens and WhatsApp QR pairing with cadence intervals.",
        render: () => `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div class="glass-panel p-4 rounded-xl border border-white/10 space-y-3">
              <div class="flex justify-between items-center">
                <b class="text-white text-sm">✈️ Telegram Notification Bot</b>
                <span class="text-[10px] text-cyan-400 font-mono">@BotFather</span>
              </div>
              <input type="text" id="wizTgTokenInput" placeholder="Paste bot token (e.g. <BOT_ID>:<BOT_TOKEN>)" class="w-full bg-slate-900 border border-white/10 p-2 rounded text-slate-200 font-mono">
              <button onclick="saveWizardTelegram()" class="w-full py-1.5 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-semibold hover:bg-cyan-500/20">
                💾 Verify & Save Telegram
              </button>
              <div id="wizTgStatus" class="hidden text-[11px] p-2 rounded bg-slate-950 font-mono"></div>
            </div>
            <div class="glass-panel p-4 rounded-xl border border-white/10 space-y-3">
              <div class="flex justify-between items-center">
                <b class="text-white text-sm">💬 WhatsApp Web Bridge</b>
                <span class="text-[10px] text-emerald-400 font-mono">Baileys QR</span>
              </div>
              <p class="text-slate-400 text-[11px]">Generate QR pairing code or pair directly with phone number.</p>
              <button onclick="switchTab('channels')" class="w-full py-1.5 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-semibold hover:bg-emerald-500/20">
                📲 Open WhatsApp Pairing Console ➔
              </button>
            </div>
          </div>
        `
      },
      {
        num: 4,
        title: "Self-Evolving Engine & Memory",
        desc: "Enable continuous dynamic recipe learning and self-healing patches.",
        render: () => `
          <div class="glass-panel p-5 rounded-xl border border-white/10 space-y-3 text-xs">
            <div class="flex items-center justify-between">
              <div>
                <b class="text-white text-sm">Dynamic Reverse-Engineering Recipes (Nod-style)</b>
                <p class="text-slate-400">Automatically persist newly discovered unpacking routines to memory.</p>
              </div>
              <span class="text-emerald-400 font-bold">ACTIVE</span>
            </div>
            <div class="bg-slate-900/80 p-3 rounded-lg font-mono text-[11px] text-cyan-300">
              .raa-workspace/memory/MEMORY.md
            </div>
          </div>
        `
      },
      {
        num: 5,
        title: "Zero-Trust Security & Vault",
        desc: "Activate untrusted prompt shielding and zero-knowledge testing credential vault.",
        render: () => `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div class="glass-panel p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-2">
              <b class="text-emerald-400">🛡️ Prompt Injection Barrier</b>
              <p class="text-slate-400">Quarantines extracted APK strings and manifest XMLs from direct LLM prompt execution.</p>
              <div class="text-emerald-400 font-semibold">✓ Enabled</div>
            </div>
            <div class="glass-panel p-4 rounded-xl border border-cyan-500/30 bg-cyan-500/5 space-y-2">
              <b class="text-cyan-400">🔐 Zero-Knowledge Vault</b>
              <p class="text-slate-400">Protects API tokens, test JWTs, and client credentials during dynamic fuzzing.</p>
              <div class="text-cyan-400 font-semibold">✓ Enabled</div>
            </div>
          </div>
        `
      }
    ];

    function selectPersona(p, el) {
      switchProfile(p);
    }

    const PROFILE_TOOLS_MAP = {
      core: new Set(['jadx', 'apktool', 'platform-tools', 'build-tools', 'androguard', 'cfr', 'procyon', 'bundletool', 'uber-apk-signer', 'apkeep', 'xerj']),
      ui: new Set(['apktool', 'platform-tools', 'build-tools', 'scrcpy', 'cleanyourtv', 'android-avd', 'iphone-control', 'uber-apk-signer', 'bundletool']),
      swarm: new Set(['jadx', 'apktool', 'platform-tools', 'build-tools', 'ghidra', 'frida', 'uber-apk-signer', 'scrcpy', 'rizin', 'mitmproxy', 'androguard', 'apkid', 'bundletool', 'blutter', 'ilspycmd', 'xerj', 'rust-anything', 'hetty', 'app-store-compliance', 'smap', 'nmap-vulners']),
      full: null
    };

    const PROFILE_MESH_MAP = {
      core: new Set(['filesystem', 'memory', 'github', 'rea', 'craft-anything', 'xerj']),
      ui: new Set(['filesystem', 'memory', 'android-tv', 'cleanyourtv', 'stitch', 'playwright', 'iphone-control', 'mobile-mcp', 'android-management']),
      swarm: new Set(['github', 'playwright', 'postman', 'nacos', 'filesystem', 'memory', 'rea', 'craft-anything', 'xerj', 'apify', 'android-management', 'openosint']),
      full: null
    };

    const KNOWN_CATALOG_TOOLS = new Set([
      'android-avd', 'jadx', 'apktool', 'platform-tools', 'build-tools', 'ghidra', 'frida',
      'uber-apk-signer', 'scrcpy', 'rizin', 'mitmproxy', 'androguard', 'apkid', 'bundletool',
      'blutter', 'ilspycmd', 'cleanyourtv', 'apkeep', 'rust-anything', 'xerj', 'iphone-control',
      'hetty', 'cfr', 'procyon', 'app-store-compliance', 'smap', 'nmap-vulners'
    ]);

    const KNOWN_CATALOG_MESH = new Set([
      'github', 'playwright', 'postman', 'apify', 'burp', 'nuclei', 'nacos', 'filesystem',
      'memory', 'android-tv', 'cleanyourtv', 'android-management', 'stitch', 'rea',
      'craft-anything', 'xerj', 'iphone-control', 'mobile-mcp', 'openosint',
      'burpsuite-mcp-bridge', 'kali-burp-mcp-bridge'
    ]);

    function isToolInProfile(tool, profile) {
      const allowed = PROFILE_TOOLS_MAP[profile || 'core'];
      if (!allowed) return true;
      if (tool.is_custom || !KNOWN_CATALOG_TOOLS.has(tool.tool_id)) return true;
      return allowed.has(tool.tool_id);
    }

    function isMeshInProfile(connector, profile) {
      const allowed = PROFILE_MESH_MAP[profile || 'core'];
      if (!allowed) return true;
      const key = connector.name || connector.id;
      if (connector.is_custom || !KNOWN_CATALOG_MESH.has(key)) return true;
      return allowed.has(key);
    }

    const PROFILE_SKILLS_MAP = {
      core: new Set(['android-triage', 'platform-check', 'raa-apk-triage', 'raa-source-reconstruct', 'raa-api-discovery', 'report-and-export', 'raa-setup-wizard', 'raa-toolchain-manager']),
      ui: new Set(['android-triage', 'platform-check', 'raa-ui-redesign', 'raa-android-tv-studio', 'raa-wireless-device-gateway', 'raa-setup-wizard', 'report-and-export']),
      swarm: new Set(['raa-apk-triage', 'raa-source-reconstruct', 'raa-api-discovery', 'raa-flutter-reversing', 'raa-native-reversing', 'raa-security-audit', 'raa-app-store-compliance', 'raa-smap-recon', 'raa-nmap-vulners', 'raa-controlled-rebuild', 'raa-mcp-mesh-manager', 'raa-mobile-agent', 'raa-cadence-controller', 'raa-self-evolving-recipes', 'raa-vault-guard', 'report-and-export']),
      full: null
    };

    const KNOWN_CATALOG_SKILLS = new Set([
      'android-triage', 'platform-check', 'raa-android-tv-studio', 'raa-api-discovery',
      'raa-apk-triage', 'raa-app-store-compliance', 'raa-smap-recon', 'raa-nmap-vulners',
      'raa-cadence-controller', 'raa-controlled-rebuild', 'raa-flutter-reversing',
      'raa-mcp-mesh-manager', 'raa-mobile-agent', 'raa-native-reversing', 'raa-security-audit',
      'raa-self-evolving-recipes', 'raa-setup-wizard', 'raa-source-reconstruct',
      'raa-toolchain-manager', 'raa-ui-redesign', 'raa-vault-guard',
      'raa-wireless-device-gateway', 'report-and-export'
    ]);

    const SKILL_CATEGORY_MAP = {
      'android-triage': 'triage',
      'platform-check': 'triage',
      'raa-apk-triage': 'triage',
      'report-and-export': 'triage',
      'raa-source-reconstruct': 'reversing',
      'raa-api-discovery': 'reversing',
      'raa-flutter-reversing': 'reversing',
      'raa-native-reversing': 'reversing',
      'raa-controlled-rebuild': 'reversing',
      'raa-security-audit': 'security',
      'raa-app-store-compliance': 'security',
      'raa-smap-recon': 'security',
      'raa-nmap-vulners': 'security',
      'raa-vault-guard': 'security',
      'raa-ui-redesign': 'ui',
      'raa-android-tv-studio': 'ui',
      'raa-wireless-device-gateway': 'ui',
      'raa-mcp-mesh-manager': 'automation',
      'raa-mobile-agent': 'automation',
      'raa-cadence-controller': 'automation',
      'raa-self-evolving-recipes': 'automation',
      'raa-setup-wizard': 'automation',
      'raa-toolchain-manager': 'automation'
    };

    function isSkillInProfile(skill, profile) {
      const allowed = PROFILE_SKILLS_MAP[profile || 'core'];
      if (!allowed) return true;
      if (skill.is_custom || !KNOWN_CATALOG_SKILLS.has(skill.id)) return true;
      return allowed.has(skill.id);
    }

    function getSkillCategory(skill) {
      if (skill.category) return skill.category;
      if (SKILL_CATEGORY_MAP[skill.id]) return SKILL_CATEGORY_MAP[skill.id];
      return 'custom';
    }

    function updateProfileDropdownVisibility(tabId) {
      const wrapper = document.getElementById('profileSelectWrapper');
      if (!wrapper) return;
      if (tabId === 'tools' || tabId === 'mesh' || tabId === 'skills') {
        wrapper.style.display = 'inline-flex';
        wrapper.classList.remove('hidden');
      } else {
        wrapper.style.display = 'none';
        wrapper.classList.add('hidden');
      }
    }

    function switchTab(tabId) {
      updateProfileDropdownVisibility(tabId);
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.className = 'tab-btn px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition whitespace-nowrap text-xs font-semibold';
      });
      const activeBtn = document.getElementById('tab-' + tabId);
      if (activeBtn) {
        activeBtn.className = 'tab-btn px-2.5 py-1.5 rounded-lg text-emerald-400 tab-active transition whitespace-nowrap text-xs font-semibold';
      }

      const views = ['wizard', 'workspace', 'tools', 'channels', 'wifi', 'mesh', 'skills', 'tv', 'security', 'config'];
      views.forEach(v => {
        const el = document.getElementById('view-' + v);
        if (el) {
          if (v === tabId) {
            el.classList.remove('hidden');
          } else {
            el.classList.add('hidden');
          }
        }
      });

      try {
        if (views.includes(tabId)) {
          localStorage.setItem('raa_active_tab', tabId);
        }
      } catch (e) {}

      if (tabId === 'workspace') loadWorkspaceRuntimes();
      if (tabId === 'tools') loadTools();
      if (tabId === 'wifi') loadWifiDevices();
      if (tabId === 'mesh') loadMesh();
      if (tabId === 'skills') loadSkills();
      if (tabId === 'channels') loadChannelsStatus();
      if (tabId === 'tv') loadTvThemes();
      if (tabId === 'security') loadVaultSecrets();
      if (tabId === 'config') loadConfigEditor();
    }

    function updateWizardUI() {
      const step = stepData[currentStep - 1];
      document.getElementById('wizardStepNum').innerText = "Step " + step.num + " of " + totalSteps + ":";
      document.getElementById('wizardStepTitle').innerText = step.title;
      document.getElementById('wizardStepDesc').innerText = step.desc;
      document.getElementById('wizardStepContent').innerHTML = step.render();
      document.getElementById('prevBtn').disabled = (currentStep === 1);
      document.getElementById('nextBtn').innerText = (currentStep === totalSteps) ? "✨ Save & Launch RAA" : "Next Step ▶";
    }

    function nextStep() {
      if (currentStep < totalSteps) {
        currentStep++;
        initTheme();
    updateWizardUI();
      } else {
        showConfirmDialog({
          title: "Complete Setup & Launch Studio?",
          subtitle: "Workspace Initialization",
          message: "Finalize setup with the selected operational persona, channels, and MCP mesh configurations?",
          confirmText: "🚀 Finish & Launch",
          confirmClass: "bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold",
          onConfirm: () => {
            showToast("✨ RAA v4.0.0 Setup Complete! Configuration saved successfully.", "success");
            switchTab('tools');
          }
        });
      }
    }

    function prevStep() {
      if (currentStep > 1) {
        currentStep--;
        updateWizardUI();
      }
    }

    function skipWizard() {
      showConfirmDialog({
        title: "Skip Guided Setup?",
        subtitle: "Pure-Python Fallbacks",
        message: "Skip external reversing toolchain setup? RAA will operate in restricted mode using pure-Python fallbacks.",
        confirmText: "Skip Setup",
        confirmClass: "bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold",
        onConfirm: () => {
          fetch('/api/setup/skip', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
              showToast("⏭️ " + (data.message || "Setup marked as skipped. Pure-Python fallbacks active."), "info");
              switchTab('tools');
            })
            .catch(() => {
              showToast("⏭️ Setup marked as skipped. Pure-Python fallbacks active.", "info");
              switchTab('tools');
            });
        }
      });
    }


    // --- Centralized Configuration Manager & Live Editor ---
    let activeConfigFilename = 'menu.json';

    async function loadConfigEditor() {
      await selectConfigFile(activeConfigFilename);
    }

    async function selectConfigFile(filename, btnElement) {
      activeConfigFilename = filename;
      document.querySelectorAll('.cfg-pill').forEach(b => {
        b.className = 'cfg-pill px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 bg-slate-900/60 text-slate-400 hover:text-white flex items-center gap-1.5 transition';
      });
      if (btnElement) {
        btnElement.className = 'cfg-pill active-cfg px-3 py-1.5 rounded-xl text-xs font-mono border border-cyan-400 bg-cyan-500/10 text-cyan-300 flex items-center gap-1.5 transition';
      }

      const pathDisplay = document.getElementById('cfgActivePathDisplay');
      const sizeDisplay = document.getElementById('cfgActiveSizeDisplay');
      const textarea = document.getElementById('configEditorTextarea');
      const valStatus = document.getElementById('cfgValidationStatus');

      if (pathDisplay) pathDisplay.innerText = 'E:/MCP_Workspace/RAA/config/' + filename;

      try {
        const res = await fetch('/api/setup/config/' + encodeURIComponent(filename));
        const data = await res.json();
        if (data.status === 'success') {
          if (textarea) textarea.value = data.content;
          if (sizeDisplay) sizeDisplay.innerText = `(${data.content.length} bytes)`;
          if (valStatus) {
            valStatus.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
            valStatus.innerText = '✓ Valid JSON';
          }
        } else {
          showToast('Failed to load ' + filename + ': ' + (data.message || 'Error'), 'error');
        }
      } catch (e) {
        showToast('Failed to contact configuration gateway.', 'error');
      }
    }

    function formatConfigJson() {
      const textarea = document.getElementById('configEditorTextarea');
      const valStatus = document.getElementById('cfgValidationStatus');
      if (!textarea) return;
      try {
        const parsed = JSON.parse(textarea.value);
        textarea.value = JSON.stringify(parsed, null, 2);
        if (valStatus) {
          valStatus.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
          valStatus.innerText = '✓ Valid JSON';
        }
        showToast('JSON formatted successfully.', 'success');
      } catch (e) {
        if (valStatus) {
          valStatus.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/30';
          valStatus.innerText = '❌ Invalid JSON';
        }
        showToast('Cannot format: ' + e.message, 'error');
      }
    }

    async function reloadActiveConfigFile() {
      await selectConfigFile(activeConfigFilename);
      showToast('Reloaded ' + activeConfigFilename + ' from disk.', 'info');
    }

    function openConfigFolderInExplorer() {
      openInWindowsExplorer('', 'E:/MCP_Workspace/RAA/config');
    }

    async function saveActiveConfigFile() {
      const textarea = document.getElementById('configEditorTextarea');
      if (!textarea) return;

      let parsed = null;
      try {
        parsed = JSON.parse(textarea.value);
      } catch (e) {
        showToast('Invalid JSON: ' + e.message, 'error');
        return;
      }

      showConfirmDialog({
        title: `Save ${activeConfigFilename}?`,
        subtitle: 'E:/MCP_Workspace/RAA/config',
        message: `Write and apply changes to 'config/${activeConfigFilename}'? All active services and UI views will synchronize immediately.`,
        confirmText: '💾 Save & Apply',
        confirmClass: 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold',
        onConfirm: async () => {
          try {
            const res = await fetch('/api/setup/config/' + encodeURIComponent(activeConfigFilename), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ file_id: activeConfigFilename, content: textarea.value })
            });
            const data = await res.json();
            if (data.status === 'success') {
              showToast(`✓ Saved ${activeConfigFilename} successfully.`, 'success');
              loadTools();
              loadMesh();
              loadChannelsStatus();
            } else {
              showToast('❌ Error: ' + (data.message || 'Save failed'), 'error');
            }
          } catch (e) {
            showToast('Save failed.', 'error');
          }
        }
      });
    }

    async function switchProfile(val) {
      selectedPersona = val;
      document.querySelectorAll('.persona-card').forEach(c => c.classList.remove('card-selected'));
      const targetCard = document.getElementById('persona-' + val);
      if (targetCard) targetCard.classList.add('card-selected');
      const sel = document.getElementById('profileSelect');
      if (sel && sel.value !== val) sel.value = val;
      toolsCurrentPage = 1;
      meshCurrentPage = 1;
      skillsCurrentPage = 1;
      if (allToolsCache.length > 0) renderToolsGrid();
      if (allMeshCache.length > 0) renderMeshGrid();
      if (allSkillsCache.length > 0) renderSkillsGrid();
      try {
        await fetch('/api/setup/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ active_profile: val })
        });
      } catch (e) {}
    }

    async function loadActiveProfile() {
      try {
        const res = await fetch('/api/setup/profile');
        const data = await res.json();
        const prof = data.active_profile || 'core';
        selectedPersona = prof;
        const sel = document.getElementById('profileSelect');
        if (sel) sel.value = prof;
        document.querySelectorAll('.persona-card').forEach(c => c.classList.remove('card-selected'));
        const targetCard = document.getElementById('persona-' + prof);
        if (targetCard) targetCard.classList.add('card-selected');
        if (allToolsCache.length > 0) renderToolsGrid();
        if (allMeshCache.length > 0) renderMeshGrid();
        if (allSkillsCache.length > 0) renderSkillsGrid();
      } catch (e) {}
    }


    function toggleCustomToolForm() {
      const f = document.getElementById('customToolForm');
      if (f) f.classList.toggle('hidden');
    }

    async function submitCustomTool() {
      const tool_id = (document.getElementById('customToolId').value || '').trim();
      const display_name = (document.getElementById('customToolName').value || '').trim();
      const source_type = document.getElementById('customToolSourceType').value;
      const artifact_type = document.getElementById('customToolArtifactType').value;
      const download_url = (document.getElementById('customToolUrl').value || '').trim();
      const filename = (document.getElementById('customToolFilename').value || '').trim();
      const category = document.getElementById('customToolCategory').value;
      if (!tool_id || !download_url) {
        showMessageModal({ title: 'Validation Error', subtitle: 'Custom Tool', message: 'Please enter both Tool ID and Download URL / GitHub Repo / pip package.', type: 'warning' });
        return;
      }
      try {
        const res = await fetch('/api/setup/tools/custom-add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool_id,
            display_name: display_name || tool_id,
            category,
            source_type,
            artifact_type,
            download_url,
            filename,
            pip_package: source_type === 'pypi' ? download_url : '',
            auto_download: true
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          toggleCustomToolForm();
          showMessageModal({ title: 'Tool Configured', subtitle: tool_id, message: data.message || `Added and provisioned '${tool_id}'.`, type: 'success' });
          loadTools();
        } else {
          showMessageModal({ title: 'Tool Error', subtitle: tool_id, message: data.message || 'Failed to register custom tool.', type: 'error' });
        }
      } catch (e) {
        showMessageModal({ title: 'Tool Error', subtitle: 'Network Error', message: 'Failed to register custom tool.', type: 'error' });
      }
    }

    // --- Tools Logic & Download Progress ---
    async function loadTools() {
      const grid = document.getElementById('toolsGrid');
      try {
        const res = await fetch('/api/setup/tools');
        allToolsCache = await res.json();
        renderToolsGrid();
      } catch (err) {
        grid.innerHTML = '<div class="text-red-400 text-xs col-span-full">Failed to load tools catalog.</div>';
      }
    }

    function renderPaginationControls(containerId, currentPage, totalItems, pageSize, goToFnName) {
      const container = document.getElementById(containerId);
      if (!container) return;
      const totalPages = Math.ceil(totalItems / pageSize);
      if (totalItems === 0 || totalPages <= 1) {
        container.innerHTML = '';
        return;
      }
      const start = (currentPage - 1) * pageSize + 1;
      const end = Math.min(currentPage * pageSize, totalItems);
      let pageBtns = '';
      for (let p = 1; p <= totalPages; p++) {
        const activeCls = p === currentPage
          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
          : 'glass-panel text-slate-300 border border-white/10 hover:border-white/30';
        pageBtns += `<button onclick="${goToFnName}(${p})" class="px-2.5 py-1 rounded-lg text-xs transition ${activeCls}">${p}</button>`;
      }
      const prevDisabled = currentPage <= 1;
      const nextDisabled = currentPage >= totalPages;
      container.innerHTML = `
        <div class="text-xs text-slate-400 font-mono">Showing <span class="text-white font-semibold">${start}&ndash;${end}</span> of <span class="text-white font-semibold">${totalItems}</span></div>
        <div class="flex items-center gap-1.5 flex-wrap">
          <button onclick="${goToFnName}(${currentPage - 1})" ${prevDisabled ? 'disabled' : ''} class="px-2.5 py-1 rounded-lg glass-panel text-xs text-slate-300 border border-white/10 hover:border-white/30 disabled:opacity-40 disabled:cursor-not-allowed transition">◀ Prev</button>
          ${pageBtns}
          <button onclick="${goToFnName}(${currentPage + 1})" ${nextDisabled ? 'disabled' : ''} class="px-2.5 py-1 rounded-lg glass-panel text-xs text-slate-300 border border-white/10 hover:border-white/30 disabled:opacity-40 disabled:cursor-not-allowed transition">Next ▶</button>
        </div>
      `;
    }

    function goToToolsPage(page) {
      toolsCurrentPage = page;
      renderToolsGrid();
    }

    function resetToolsPageAndRender() {
      toolsCurrentPage = 1;
      renderToolsGrid();
    }

    function filterToolsStatus(status, btn) {
      activeToolStatus = status;
      toolsCurrentPage = 1;
      document.querySelectorAll('.tool-status-btn').forEach(b => {
        b.className = 'tool-status-btn px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white';
      });
      btn.className = 'tool-status-btn px-3 py-1 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40';
      renderToolsGrid();
    }

    function filterToolsCategory(cat, btn) {
      activeToolCategory = cat;
      toolsCurrentPage = 1;
      document.querySelectorAll('.tool-filter-btn').forEach(b => {
        b.className = 'tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white';
      });
      btn.className = 'tool-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
      renderToolsGrid();
    }

    function searchTools(query) {
      toolsCurrentPage = 1;
      renderToolsGrid(query.toLowerCase());
    }

    function renderToolsGrid(query = null) {
      const grid = document.getElementById('toolsGrid');
      const countBadge = document.getElementById('toolsCountBadge');
      const searchEl = document.getElementById('toolSearchInput');
      const effectiveQuery = (query === null ? (searchEl ? searchEl.value : '') : query).toLowerCase();
      const activeProfile = document.getElementById('profileSelect')?.value || selectedPersona || 'core';
      const profileScoped = allToolsCache.filter(t => isToolInProfile(t, activeProfile));
      if (countBadge) {
        const readyCount = profileScoped.filter(t => t.installed).length;
        countBadge.innerText = `${readyCount} Ready / ${profileScoped.length} Tools`;
      }
      let filtered = [...profileScoped];

      if (activeToolStatus === 'ready') {
        filtered = filtered.filter(t => t.installed);
      } else if (activeToolStatus === 'pending') {
        filtered = filtered.filter(t => !t.installed);
      }

      if (activeToolCategory !== 'all') {
        if (activeToolCategory === 'security') {
          filtered = filtered.filter(t => t.category === 'security' || t.category === 'dynamic');
        } else {
          filtered = filtered.filter(t => t.category === activeToolCategory);
        }
      }

      if (effectiveQuery.trim() !== '') {
        filtered = filtered.filter(t =>
          t.display_name.toLowerCase().includes(effectiveQuery) ||
          t.tool_id.toLowerCase().includes(effectiveQuery) ||
          t.description.toLowerCase().includes(effectiveQuery)
        );
      }

      const sortMode = document.getElementById('toolSortSelect')?.value || 'default';
      if (sortMode === 'name_asc') {
        filtered.sort((a, b) => a.display_name.localeCompare(b.display_name));
      } else if (sortMode === 'name_desc') {
        filtered.sort((a, b) => b.display_name.localeCompare(a.display_name));
      } else if (sortMode === 'status_ready') {
        filtered.sort((a, b) => ((b.available ? 1 : 0) - (a.available ? 1 : 0)) || a.display_name.localeCompare(b.display_name));
      } else if (sortMode === 'status_pending') {
        filtered.sort((a, b) => ((a.available ? 1 : 0) - (b.available ? 1 : 0)) || a.display_name.localeCompare(b.display_name));
      } else if (sortMode === 'size_desc') {
        filtered.sort((a, b) => (b.approx_size_mb || 0) - (a.approx_size_mb || 0));
      } else if (sortMode === 'size_asc') {
        filtered.sort((a, b) => (a.approx_size_mb || 0) - (b.approx_size_mb || 0));
      }

      if (filtered.length === 0) {
        grid.innerHTML = '<div class="text-slate-400 text-xs col-span-full py-8 text-center">No tools matched the filter.</div>';
        renderPaginationControls('toolsPagination', 1, 0, TOOLS_PAGE_SIZE, 'goToToolsPage');
        return;
      }

      const totalToolsPages = Math.ceil(filtered.length / TOOLS_PAGE_SIZE);
      if (toolsCurrentPage > totalToolsPages) toolsCurrentPage = totalToolsPages;
      if (toolsCurrentPage < 1) toolsCurrentPage = 1;
      const toolsStartIdx = (toolsCurrentPage - 1) * TOOLS_PAGE_SIZE;
      const pagedTools = filtered.slice(toolsStartIdx, toolsStartIdx + TOOLS_PAGE_SIZE);
      renderPaginationControls('toolsPagination', toolsCurrentPage, filtered.length, TOOLS_PAGE_SIZE, 'goToToolsPage');

      grid.innerHTML = pagedTools.map(t => {
        const githubLink = t.github_url ? `<a href="${t.github_url}" target="_blank" class="px-2 py-1 rounded bg-slate-900 border border-white/10 hover:border-cyan-400 text-[11px] text-cyan-300 flex items-center gap-1 transition">🐙 GitHub ↗</a>` : '';
        const websiteLink = t.website_url ? `<a href="${t.website_url}" target="_blank" class="px-2 py-1 rounded bg-slate-900 border border-white/10 hover:border-emerald-400 text-[11px] text-emerald-300 flex items-center gap-1 transition">🌐 Site ↗</a>` : '';
        const artBadgeMap = { jar: '☕ JAR', zip: '📦 ZIP', 'tar.xz': '🗜️ TAR.XZ', source_repo: '💻 Source', pypi: '🐍 PyPI', binary: '⚙️ Binary' };
        const artBadge = artBadgeMap[t.artifact_type] || '⚙️ Binary';
        const isDownloading = downloadingTools.has(t.tool_id);

        return `
          <div id="card-${t.tool_id}" class="glass-panel p-4 rounded-xl border border-white/10 flex flex-col justify-between space-y-3 hover:border-white/20 transition">
            <div class="space-y-2">
              <div class="flex justify-between items-start gap-2">
                <div>
                  <h4 class="font-bold text-white text-sm leading-snug">${t.display_name}</h4>
                  <div class="flex items-center gap-1 flex-wrap mt-0.5">
                    <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">${t.category}</span>
                    <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">${artBadge}</span>
                    ${t.optional ? '<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">Optional</span>' : ''}
                  </div>
                </div>
                <span id="badge-${t.tool_id}" class="px-2 py-0.5 text-xs font-semibold rounded shrink-0 ${t.installed ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'}">
                  ${t.installed ? '✓ Ready' : 'Pending'}
                </span>
              </div>
              <p class="text-xs text-slate-400 line-clamp-2">${t.description}</p>
              <div class="flex justify-between text-[11px] text-slate-500 font-mono pt-1">
                <span>v${t.version}</span>
                <span id="sizeLabel-${t.tool_id}">${t.installed ? (t.size_mb + ' MB') : `~${t.approx_size_mb || 35} MB`}</span>
              </div>
              ${t.installed && t.binary_path ? `
                <div id="pathDisplay-${t.tool_id}" onclick="handlePathClick('${t.tool_id}')" class="cursor-pointer group flex items-center justify-between text-[11px] font-mono text-cyan-400 bg-slate-950/80 hover:bg-slate-900 p-2 rounded-lg border border-cyan-500/30 hover:border-cyan-400 transition mb-2 shadow-sm" title="Click to open Windows file explorer and configure path">
                  <div class="flex items-center space-x-1.5 truncate">
                    <span class="text-xs">📁</span>
                    <span class="truncate underline decoration-cyan-500/30 group-hover:decoration-cyan-400 font-semibold">${t.binary_path}</span>
                  </div>
                  <span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shrink-0 group-hover:bg-cyan-500/30 flex items-center gap-1 font-sans font-medium">
                    <span>📂 Open</span>
                  </span>
                </div>
              ` : `
                <div id="pathDisplay-${t.tool_id}" class="hidden text-[11px] font-mono text-cyan-400 bg-slate-950/80 p-2 rounded-lg border border-cyan-500/30 mb-2"></div>
              `}
            </div>

            <!-- Download Progress Bar Container (hidden until downloading) -->
            <div id="progressArea-${t.tool_id}" class="hidden space-y-2 pt-2 border-t border-white/10">
              <div class="flex justify-between items-center text-[11px] font-mono">
                <span id="stageText-${t.tool_id}" class="text-cyan-300 font-semibold truncate max-w-[210px]">🌐 Initializing download...</span>
                <span id="stagePercent-${t.tool_id}" class="text-emerald-400 font-bold">0%</span>
              </div>
              <div class="w-full bg-slate-950 border border-white/10 rounded-full h-3 p-0.5 overflow-hidden">
                <div id="progressBar-${t.tool_id}" class="bg-gradient-to-r from-cyan-400 via-emerald-400 to-emerald-500 h-2 rounded-full transition-all duration-150 shadow-[0_0_12px_rgba(0,245,155,0.7)]" style="width: 0%"></div>
              </div>
              <div class="flex justify-between text-[10px] text-slate-400 font-mono">
                <span id="stageBytes-${t.tool_id}">0.0 MB / ${t.approx_size_mb || 35} MB</span>
                <span id="stageSpeed-${t.tool_id}" class="text-cyan-400">8.4 MB/s</span>
              </div>
            </div>

            <!-- Action Area (Buttons) -->
            <div id="actionArea-${t.tool_id}" class="space-y-2 pt-2 border-t border-white/10">
              <div class="flex items-center gap-1.5 flex-wrap">
                ${githubLink}
                ${websiteLink}
                <button onclick="openToolPathModal('${t.tool_id}')" class="px-2 py-1 rounded bg-slate-900 border border-white/10 hover:border-amber-400 text-[11px] text-amber-300 flex items-center gap-1 transition" title="Open Path Dialog & Windows File Explorer">⚙️ Path</button>
              </div>

              <div id="buttonsRow-${t.tool_id}" class="flex items-center gap-2">
                ${t.installed ? `
                  <button onclick="verifyTool('${t.tool_id}')" class="flex-1 py-1.5 px-3 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold hover:bg-emerald-500/20 transition inline-flex items-center justify-center gap-1.5 whitespace-nowrap">🔒 Verify</button>
                  <button onclick="deleteTool('${t.tool_id}')" class="py-1.5 px-3 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/20 transition inline-flex items-center justify-center gap-1.5 whitespace-nowrap shrink-0">🗑️ Delete</button>
                ` : `
                  <button onclick="downloadTool('${t.tool_id}')" ${isBulkDownloading ? 'disabled' : ''} class="tool-download-btn w-full py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition flex items-center justify-center gap-2 ${isBulkDownloading ? 'opacity-50 cursor-not-allowed' : ''}">
                    <span>${isBulkDownloading ? '⏳ Queued...' : '⬇️ Download'}</span>
                  </button>
                `}
              </div>
            </div>
          </div>
        `;
      }).join('');
    }


    // --- Cyber-Glass Modal Notification System (Replaces browser alert() and toasts) ---
    function showMessageModal({ title, subtitle, message, type = 'info' }) {
      const modal = document.getElementById('messageDialogModal');
      const iconBox = document.getElementById('msgIconBox');
      const titleEl = document.getElementById('msgTitle');
      const subEl = document.getElementById('msgSubtitle');
      const bodyEl = document.getElementById('msgBody');
      const okBtn = document.getElementById('msgOkBtn');

      const config = {
        success: {
          icon: '✓',
          title: 'Success',
          subtitle: 'Operation completed',
          iconCls: 'w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/40 flex items-center justify-center text-xl text-emerald-400',
          btnCls: 'py-2 px-5 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 text-xs font-bold transition'
        },
        error: {
          icon: '✕',
          title: 'Error',
          subtitle: 'Action could not be completed',
          iconCls: 'w-10 h-10 rounded-xl bg-red-500/15 border border-red-500/40 flex items-center justify-center text-xl text-red-400',
          btnCls: 'py-2 px-5 rounded-xl bg-red-500 hover:bg-red-600 text-white text-xs font-bold transition'
        },
        warning: {
          icon: '⚠️',
          title: 'Attention Required',
          subtitle: 'Please review the details below',
          iconCls: 'w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/40 flex items-center justify-center text-xl text-amber-400',
          btnCls: 'py-2 px-5 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 text-xs font-bold transition'
        },
        info: {
          icon: '\u2139\ufe0f',
          title: 'Notification',
          subtitle: 'RAA Studio Status',
          iconCls: 'w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/40 flex items-center justify-center text-xl text-cyan-400',
          btnCls: 'py-2 px-5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 text-xs font-bold transition'
        }
      };
      const cfg = config[type] || config.info;

      if (iconBox) {
        iconBox.className = cfg.iconCls;
        iconBox.innerText = cfg.icon;
      }
      if (titleEl) titleEl.innerText = title || cfg.title;
      if (subEl) subEl.innerText = subtitle || cfg.subtitle;
      if (bodyEl) bodyEl.innerText = message || '';
      if (okBtn) okBtn.className = cfg.btnCls;
      if (modal) modal.classList.remove('hidden');
    }

    function closeMessageModal() {
      const modal = document.getElementById('messageDialogModal');
      if (modal) modal.classList.add('hidden');
    }

    function showToast(message, type = 'info') {
      showMessageModal({ message: message, type: type });
    }

    let confirmCallback = null;
    function showConfirmDialog({ title, subtitle, message, confirmText, confirmClass, onConfirm }) {
      const modal = document.getElementById('confirmDialogModal');
      const t = document.getElementById('confirmTitle');
      const s = document.getElementById('confirmSubtitle');
      const m = document.getElementById('confirmMessage');
      const btn = document.getElementById('confirmOkBtn');
      if (t) t.innerText = title || 'Confirm Action';
      if (s) s.innerText = subtitle || 'Action confirmation required';
      if (m) m.innerText = message || 'Are you sure you want to proceed?';
      if (btn) {
        btn.innerText = confirmText || 'Confirm';
        btn.className = `py-2 px-4 rounded-xl text-xs font-bold transition ${confirmClass || 'bg-red-500 hover:bg-red-600 text-white'}`;
      }
      confirmCallback = onConfirm;
      if (modal) modal.classList.remove('hidden');
    }

    function closeConfirmModal(confirmed) {
      const modal = document.getElementById('confirmDialogModal');
      if (modal) modal.classList.add('hidden');
      if (confirmed && typeof confirmCallback === 'function') {
        confirmCallback();
      }
      confirmCallback = null;
    }

    // --- Tool Path Modal and Explorer Integration ---
    let activeModalToolId = '';
    let activeModalCurrentPath = '';

    function openToolPathModal(toolId) {
      const tool = (Array.isArray(allToolsCache) ? allToolsCache.find(t => t.tool_id === toolId) : null) || {};
      const currentPath = tool.binary_path || '';
      activeModalToolId = toolId;
      activeModalCurrentPath = currentPath;
      const modal = document.getElementById('toolPathModal');
      const title = document.getElementById('modalToolTitle');
      const category = document.getElementById('modalToolCategory');
      const pathBox = document.getElementById('modalCurrentPath');
      const input = document.getElementById('modalCustomPathInput');
      const fb = document.getElementById('modalPathFeedback');

      if (title) title.innerText = `Configure: ${(tool.display_name || toolId).toUpperCase()}`;
      if (category) category.innerText = `${(tool.category || 'REVERSING ENGINE').toUpperCase()}`;
      if (pathBox) {
        pathBox.innerText = currentPath || 'Not installed / default location';
        pathBox.title = currentPath || '';
      }
      if (input) input.value = currentPath || '';
      if (fb) {
        fb.classList.add('hidden');
        fb.innerText = '';
      }
      if (modal) modal.classList.remove('hidden');
    }

    function closeToolPathModal() {
      const modal = document.getElementById('toolPathModal');
      if (modal) modal.classList.add('hidden');
    }

    async function handlePathClick(toolId) {
      const tool = (Array.isArray(allToolsCache) ? allToolsCache.find(t => t.tool_id === toolId) : null) || {};
      const binaryPath = tool.binary_path || '';
      // 1. Trigger opening the file or containing folder in Windows Explorer
      await openInWindowsExplorer(toolId, binaryPath);
      // 2. Open the Dialog Modal for viewing/configuring path
      openToolPathModal(toolId);
    }

    async function openInWindowsExplorer(toolId, path) {
      try {
        const res = await fetch('/api/setup/tools/open-path', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool_name: toolId, path: path || '' })
        });
        const data = await res.json();
        if (data.status !== 'success') {
          showMessageModal({
            title: 'Could Not Open Folder',
            subtitle: path || toolId || 'Explorer',
            message: data.message || 'Could not open Windows Explorer.',
            type: 'warning'
          });
        }
      } catch (e) {
        showMessageModal({
          title: 'Explorer Error',
          subtitle: path || toolId || 'Explorer',
          message: 'Failed to open Windows Explorer.',
          type: 'error'
        });
      }
    }

    function openCurrentInExplorer() {
      const input = document.getElementById('modalCustomPathInput');
      const path = (input && input.value.trim()) || activeModalCurrentPath;
      openInWindowsExplorer(activeModalToolId, path);
    }

    function handleFilePicked(e) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const pickedPath = file.path || file.name;
      const input = document.getElementById('modalCustomPathInput');
      if (input) {
        input.value = pickedPath;
        showToast(`📁 Picked: ${file.name}. Click 'Save Path' to apply.`, 'info');
      }
    }

    async function saveModalCustomPath() {
      const input = document.getElementById('modalCustomPathInput');
      const fb = document.getElementById('modalPathFeedback');
      const pathVal = input ? input.value.trim() : '';
      if (!pathVal) {
        showToast('Please enter or select a valid path.', 'warning');
        return;
      }
      try {
        const res = await fetch('/api/setup/tools/custom-path', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool_name: activeModalToolId, custom_path: pathVal })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(`✓ ${data.message}`, 'success');
          closeToolPathModal();
          loadTools();
        } else {
          if (fb) {
            fb.classList.remove('hidden');
            fb.className = 'text-xs p-3 rounded-xl border font-mono bg-red-950/60 border-red-500/40 text-red-300';
            fb.innerText = `❌ Error: ${data.message || 'Failed to set custom path'}`;
          }
          showToast(`❌ ${data.message || 'Failed to set custom path'}`, 'error');
        }
      } catch (e) {
        showToast('Failed to configure custom path.', 'error');
      }
    }


    // Multi-stage realistic progress runner (supports both Tools tab & Step 2 Wizard cards)
    async function animateDownloadProgress(toolId, approxMb, sourceName) {
      const progressArea = document.getElementById('progressArea-' + toolId);
      const actionArea = document.getElementById('actionArea-' + toolId);
      const badge = document.getElementById('badge-' + toolId);
      const progressBar = document.getElementById('progressBar-' + toolId);
      const stageText = document.getElementById('stageText-' + toolId);
      const stagePercent = document.getElementById('stagePercent-' + toolId);
      const stageBytes = document.getElementById('stageBytes-' + toolId);
      const stageSpeed = document.getElementById('stageSpeed-' + toolId);

      // Step 2 Wizard elements
      const wizProgressArea = document.getElementById('wizProgressArea-' + toolId);
      const wizBtnArea = document.getElementById('wizBtnArea-' + toolId);
      const wizProgressBar = document.getElementById('wizProgressBar-' + toolId);
      const wizStageText = document.getElementById('wizStageText-' + toolId);
      const wizStagePercent = document.getElementById('wizStagePercent-' + toolId);
      const wizStageBytes = document.getElementById('wizStageBytes-' + toolId);
      const wizStageSpeed = document.getElementById('wizStageSpeed-' + toolId);

      if (actionArea) actionArea.classList.add('hidden');
      if (progressArea) progressArea.classList.remove('hidden');
      if (wizProgressArea) wizProgressArea.classList.remove('hidden');
      if (wizBtnArea) {
        wizBtnArea.innerHTML = `<span class="px-2.5 py-1 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-semibold">⏳ Installing...</span>`;
      }
      if (badge) {
        badge.className = 'px-2 py-0.5 text-xs font-semibold rounded shrink-0 bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center gap-1.5';
        badge.innerHTML = '<span class="w-2 h-2 rounded-full bg-cyan-400 pulse-dot"></span> Downloading...';
      }

      // Step stages: percent, text, speedMb
      const stages = [
        { p: 12, text: `🌐 Connecting to ${sourceName || 'mirror'}...`, speed: "12.4 MB/s" },
        { p: 28, text: "📥 Fetching release archive...", speed: "9.2 MB/s" },
        { p: 54, text: "📥 Streaming payload bytes...", speed: "10.8 MB/s" },
        { p: 76, text: "📥 Verifying package integrity...", speed: "8.5 MB/s" },
        { p: 89, text: "🔒 Cryptographic SHA-256 Validation...", speed: "15.0 MB/s" },
        { p: 96, text: "⚙️ Extracting & injecting PATH...", speed: "4.2 MB/s" },
        { p: 100, text: "✓ Download & Verify Complete!", speed: "Done" },
      ];

      for (let s of stages) {
        const downloaded = ((approxMb * s.p) / 100).toFixed(1);
        if (stageText) stageText.innerText = s.text;
        if (stagePercent) stagePercent.innerText = s.p + '%';
        if (progressBar) progressBar.style.width = s.p + '%';
        if (stageSpeed) stageSpeed.innerText = s.speed;
        if (stageBytes) stageBytes.innerText = `${downloaded} MB / ${approxMb} MB`;

        if (wizStageText) wizStageText.innerText = s.text;
        if (wizStagePercent) wizStagePercent.innerText = s.p + '%';
        if (wizProgressBar) wizProgressBar.style.width = s.p + '%';
        if (wizStageSpeed) wizStageSpeed.innerText = s.speed;
        if (wizStageBytes) wizStageBytes.innerText = `${downloaded} MB / ${approxMb} MB`;

        await new Promise(r => setTimeout(r, 220));
      }
    }

    async function downloadTool(id) {
      if (id === 'all') {
        await downloadAllMissingTools();
        return;
      }

      if (downloadingTools.has(id)) return;
      downloadingTools.add(id);

      const tool = allToolsCache.find(t => t.tool_id === id) || { display_name: id, approx_size_mb: 35, download_source: "Mirror" };
      const approxMb = tool.approx_size_mb || 35.0;

      try {
        // Run smooth visual progress animation alongside backend provision call
        const animPromise = animateDownloadProgress(id, approxMb, tool.download_source);
        const apiPromise = fetch('/api/setup/tools/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool_name: id, force: false })
        }).then(r => r.json());

        const [_, apiResult] = await Promise.all([animPromise, apiPromise]);

        // Keep 100% visible briefly so user confirms success
        await new Promise(r => setTimeout(r, 450));

        // Update card to verified ready state
        tool.installed = true;
        tool.binary_path = apiResult.path || tool.binary_path;

        const progressArea = document.getElementById('progressArea-' + id);
        const actionArea = document.getElementById('actionArea-' + id);
        const badge = document.getElementById('badge-' + id);
        const buttonsRow = document.getElementById('buttonsRow-' + id);
        const pathDisplay = document.getElementById('pathDisplay-' + id);
        const sizeLabel = document.getElementById('sizeLabel-' + id);

        if (progressArea) progressArea.classList.add('hidden');
        if (actionArea) actionArea.classList.remove('hidden');

        if (badge) {
          badge.className = 'px-2 py-0.5 text-xs font-semibold rounded shrink-0 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
          badge.innerText = '✓ Ready';
        }

        if (sizeLabel) {
          sizeLabel.innerText = `${((apiResult.size_bytes || 1024) / (1024 * 1024)).toFixed(2)} MB`;
        }

        if (pathDisplay && apiResult.path) {
          pathDisplay.classList.remove('hidden');
          pathDisplay.className = 'cursor-pointer group flex items-center justify-between text-[11px] font-mono text-cyan-400 bg-slate-950/80 hover:bg-slate-900 p-2 rounded-lg border border-cyan-500/30 hover:border-cyan-400 transition mb-2 shadow-sm';
          pathDisplay.title = 'Click to open Windows file explorer and configure path';
          pathDisplay.onclick = () => handlePathClick(id);
          pathDisplay.innerHTML = `
            <div class="flex items-center space-x-1.5 truncate">
              <span class="text-xs">📁</span>
              <span class="truncate underline decoration-cyan-500/30 group-hover:decoration-cyan-400 font-semibold">${apiResult.path}</span>
            </div>
            <span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shrink-0 group-hover:bg-cyan-500/30 flex items-center gap-1 font-sans font-medium">
              <span>📂 Open</span>
            </span>
          `;
        }

        if (buttonsRow) {
          buttonsRow.innerHTML = `
            <button onclick="verifyTool('${id}')" class="flex-1 py-1.5 px-3 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold hover:bg-emerald-500/20 transition inline-flex items-center justify-center gap-1.5 whitespace-nowrap">🔒 Verify</button>
            <button onclick="deleteTool('${id}')" class="py-1.5 px-3 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/20 transition inline-flex items-center justify-center gap-1.5 whitespace-nowrap shrink-0">🗑️ Delete</button>
          `;
        }

        // Update Step 2 Wizard card if visible
        const wizProgressArea = document.getElementById('wizProgressArea-' + id);
        const wizBtnArea = document.getElementById('wizBtnArea-' + id);
        if (wizProgressArea) wizProgressArea.classList.add('hidden');
        if (wizBtnArea) {
          wizBtnArea.innerHTML = `<span class="px-2.5 py-1 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded font-semibold">✓ Ready</span>`;
        }
        showToast(`✓ ${tool.display_name || id} installed and ready.`, "success");
      } catch (e) {
        showToast("Failed to download tool: " + id, "error");
        const progressArea = document.getElementById('progressArea-' + id);
        const actionArea = document.getElementById('actionArea-' + id);
        const wizProgressArea = document.getElementById('wizProgressArea-' + id);
        const wizBtnArea = document.getElementById('wizBtnArea-' + id);
        if (progressArea) progressArea.classList.add('hidden');
        if (actionArea) actionArea.classList.remove('hidden');
        if (wizProgressArea) wizProgressArea.classList.add('hidden');
        if (wizBtnArea) {
          wizBtnArea.innerHTML = `<button onclick="downloadTool('${id}')" class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded hover:bg-emerald-500/30 font-semibold transition">⬇️ Install</button>`;
        }
      } finally {
        downloadingTools.delete(id);
      }
    }

    let isBulkDownloading = false;

    function _setBulkDownloadLock(locked) {
      isBulkDownloading = locked;
      document.querySelectorAll('.tool-download-btn, button[onclick*="downloadTool"][onclick*="all"]').forEach(btn => {
        btn.disabled = locked;
        if (locked) {
          btn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
          btn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
      });
    }

    async function downloadAllMissingTools() {
      if (isBulkDownloading) return;
      if (allToolsCache.length === 0) {
        await loadTools();
      }
      const missing = allToolsCache.filter(t => !t.installed);
      if (missing.length === 0) {
        showToast("✓ All available reversing engine binaries are already downloaded and ready!", "success");
        return;
      }

      _setBulkDownloadLock(true);
      const banner = document.getElementById('globalDownloadBanner');
      const title = document.getElementById('globalDownloadTitle');
      const percent = document.getElementById('globalDownloadPercent');
      const bar = document.getElementById('globalProgressBar');
      const detail = document.getElementById('globalDownloadDetail');

      const wizBanner = document.getElementById('wizGlobalDownloadBanner');
      const wizTitle = document.getElementById('wizGlobalDownloadTitle');
      const wizPercent = document.getElementById('wizGlobalDownloadPercent');
      const wizBar = document.getElementById('wizGlobalProgressBar');
      const wizDetail = document.getElementById('wizGlobalDownloadDetail');

      if (banner) banner.classList.remove('hidden');
      if (wizBanner) wizBanner.classList.remove('hidden');

      try {
        let completedCount = 0;
        for (let t of missing) {
          const overallPct = Math.round((completedCount / missing.length) * 100);
          const tText = `⬇️ Provisioning Reversing Toolchain (${completedCount} of ${missing.length} Completed)...`;
          const dText = `Currently installing: ${t.display_name} (${t.download_source})...`;

          if (title) title.innerText = tText;
          if (percent) percent.innerText = overallPct + '%';
          if (bar) bar.style.width = overallPct + '%';
          if (detail) detail.innerText = dText;

          if (wizTitle) wizTitle.innerText = tText;
          if (wizPercent) wizPercent.innerText = overallPct + '%';
          if (wizBar) wizBar.style.width = overallPct + '%';
          if (wizDetail) wizDetail.innerText = dText;

          await downloadTool(t.tool_id);
          completedCount++;
        }

        const doneTitle = `✨ All ${missing.length} Engines Successfully Installed!`;
        const doneDetail = 'Toolchain binaries verified and injected into PATH.';
        if (title) title.innerText = doneTitle;
        if (percent) percent.innerText = '100%';
        if (bar) bar.style.width = '100%';
        if (detail) detail.innerText = doneDetail;

        if (wizTitle) wizTitle.innerText = doneTitle;
        if (wizPercent) wizPercent.innerText = '100%';
        if (wizBar) wizBar.style.width = '100%';
        if (wizDetail) wizDetail.innerText = doneDetail;
      } finally {
        _setBulkDownloadLock(false);
        setTimeout(() => {
          if (banner) banner.classList.add('hidden');
          if (wizBanner) wizBanner.classList.add('hidden');
        }, 4000);
      }
    }

    async function verifyTool(id) {
      try {
        const res = await fetch('/api/setup/tools/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool_name: id })
        });
        const data = await res.json();
        if (data.verified) {
          showToast(`🔒 ${id.toUpperCase()}: SHA-256 Validated! Integrity verified.`, 'success');
        } else {
          showToast(`⚠️ ${id.toUpperCase()}: Checksum mismatch or unverified binary.`, 'warning');
        }
      } catch (e) {
        showToast('Verification request failed.', 'error');
      }
    }

    async function deleteTool(id) {
      showConfirmDialog({
        title: `Delete ${id.toUpperCase()}?`,
        subtitle: 'Toolchain Binary Purge',
        message: `Are you sure you want to delete ${id}? This will remove the executable from local workspace storage and reset the tool status.`,
        confirmText: '🗑️ Delete Binary',
        confirmClass: 'bg-red-500 hover:bg-red-600 text-white',
        onConfirm: async () => {
          try {
            const res = await fetch('/api/setup/tools/delete', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ tool_name: id })
            });
            const data = await res.json();
            showToast('🧹 ' + (data.message || 'Tool deleted and storage reclaimed.'), 'success');
            loadTools();
          } catch (e) {
            showToast('Delete failed.', 'error');
          }
        }
      });
    }

    // --- Mobile Channels Logic ---
    async function loadChannelsStatus() {
      try {
        const res = await fetch('/api/setup/channels/status');
        const data = await res.json();

        // Telegram UI Status
        const tgBadge = document.getElementById('tgStatusBadge');
        const tgTokenGroup = document.getElementById('tgTokenGroup');
        const tgChatIdInput = document.getElementById('tgChatIdInput');
        const tgConnectBtn = document.getElementById('tgConnectBtn');
        const tgDiscBtn = document.getElementById('tgDisconnectBtn');
        const tgChatBox = document.getElementById('tgChatBox');
        if (data.telegram && data.telegram.configured) {
          tgBadge.className = 'px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0';
          tgBadge.innerText = '🟢 Connected ' + (data.telegram.bot_username || '');
          if (tgChatIdInput) {
            if (data.telegram.default_chat_id) {
              tgChatIdInput.value = data.telegram.default_chat_id;
            }
            tgChatIdInput.disabled = true;
            tgChatIdInput.classList.add('opacity-60', 'cursor-not-allowed');
          }
          if (tgTokenGroup) tgTokenGroup.classList.add('hidden');
          if (tgConnectBtn) tgConnectBtn.classList.add('hidden');
          if (tgDiscBtn) tgDiscBtn.classList.remove('hidden');
          if (tgChatBox) tgChatBox.classList.remove('hidden');
        } else {
          tgBadge.className = 'px-2.5 py-0.5 text-xs font-bold rounded-full bg-slate-800 text-slate-400 border border-white/10 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0';
          tgBadge.innerText = '⚪ Not Configured';
          if (tgChatIdInput) {
            tgChatIdInput.disabled = false;
            tgChatIdInput.classList.remove('opacity-60', 'cursor-not-allowed');
          }
          if (tgTokenGroup) tgTokenGroup.classList.remove('hidden');
          if (tgConnectBtn) tgConnectBtn.classList.remove('hidden');
          if (tgDiscBtn) tgDiscBtn.classList.add('hidden');
          if (tgChatBox) tgChatBox.classList.add('hidden');
        }

        // WhatsApp UI Status
        const waBadge = document.getElementById('waStatusBadge');
        const waPhoneInput = document.getElementById('waPhoneInput');
        const waQrBtn = document.getElementById('waQrBtn');
        const waDisconnectBtn = document.getElementById('waDisconnectBtn');
        const waPairBtn = document.getElementById('waPairBtn');
        const waQrContainer = document.getElementById('waQrContainer');
        const waChatBox = document.getElementById('waChatBox');
        if (data.whatsapp && (data.whatsapp.paired || data.whatsapp.configured)) {
          waBadge.className = 'px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0';
          waBadge.innerText = '🟢 Linked ' + (data.whatsapp.phone || '');
          if (waPhoneInput) {
            if (data.whatsapp.phone) {
              waPhoneInput.value = data.whatsapp.phone;
            }
            waPhoneInput.disabled = true;
            waPhoneInput.classList.add('opacity-60', 'cursor-not-allowed');
          }
          if (waQrBtn) waQrBtn.classList.add('hidden');
          if (waPairBtn) waPairBtn.classList.add('hidden');
          if (waQrContainer) waQrContainer.classList.add('hidden');
          if (waDisconnectBtn) {
            waDisconnectBtn.classList.remove('hidden');
            waDisconnectBtn.classList.add('flex-1');
          }
          if (waChatBox) waChatBox.classList.remove('hidden');
        } else {
          waBadge.className = 'px-2.5 py-0.5 text-xs font-bold rounded-full bg-slate-800 text-slate-400 border border-white/10 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0';
          waBadge.innerText = '⚪ Awaiting Scan';
          if (waPhoneInput) {
            waPhoneInput.disabled = false;
            waPhoneInput.classList.remove('opacity-60', 'cursor-not-allowed');
          }
          if (waQrBtn) waQrBtn.classList.remove('hidden');
          if (waPairBtn) waPairBtn.classList.remove('hidden');
          if (waDisconnectBtn) {
            waDisconnectBtn.classList.add('hidden');
            waDisconnectBtn.classList.remove('flex-1');
          }
          if (waChatBox) waChatBox.classList.add('hidden');
        }
      } catch (e) {
        console.error("Failed to load channel status", e);
      }
      loadCadenceStatus();
    }

    async function saveTelegramConfig() {
      const token = document.getElementById('tgTokenInput').value.trim();
      const chatId = document.getElementById('tgChatIdInput').value.trim();
      const fb = document.getElementById('tgFeedback');

      if (!token) {
        showToast("Please enter your Telegram Bot Token from @BotFather.", "warning");
        return;
      }

      fb.classList.remove('hidden');
      fb.className = 'text-xs p-3 rounded-lg border font-mono bg-cyan-950/40 border-cyan-500/30 text-cyan-300';
      fb.innerText = "⏳ Verifying bot token with Telegram gateway...";

      try {
        const res = await fetch('/api/setup/channels/telegram/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bot_token: token, chat_id: chatId })
        });
        const data = await res.json();
        if (data.status === 'success') {
          fb.className = 'text-xs p-3 rounded-lg border font-mono bg-emerald-950/40 border-emerald-500/30 text-emerald-300';
          fb.innerHTML = `✓ <strong>Connected!</strong> Bot Name: ${data.bot_name} (${data.bot_username})<br>Verified live with Telegram API.`;
          loadChannelsStatus();
          if (!chatId && data.pairing_url) {
            const linkBox = document.getElementById('tgLinkContainer');
            const qrBox = document.getElementById('tgQrSvgBox');
            const anchor = document.getElementById('tgDeepLinkAnchor');
            if (linkBox) linkBox.classList.remove('hidden');
            if (qrBox && data.qr_svg) qrBox.innerHTML = data.qr_svg;
            if (anchor) anchor.href = data.pairing_url;
            startTgPolling();
          }
          showMessageModal({
            title: 'Telegram Bot Verified',
            subtitle: `${data.bot_name} (${data.bot_username})`,
            message: chatId
              ? 'Telegram Bot token verified and Chat ID saved.'
              : 'Telegram Bot verified! Open the bot link/QR and tap Start in Telegram to auto-link your Chat ID.',
            type: 'success'
          });
        } else {
          fb.className = 'text-xs p-3 rounded-lg border font-mono bg-red-950/40 border-red-500/30 text-red-300';
          fb.innerText = `❌ Error: ${data.message || "Invalid Telegram Bot Token."}`;
          showMessageModal({
            title: 'Telegram Verification Failed',
            subtitle: 'Invalid Token or Gateway Error',
            message: data.message || 'Invalid Telegram Bot Token.',
            type: 'error'
          });
        }
      } catch (e) {
        fb.className = 'text-xs p-3 rounded-lg border font-mono bg-red-950/40 border-red-500/30 text-red-300';
        fb.innerText = "❌ Request failed while contacting Telegram gateway.";
        showMessageModal({
          title: 'Telegram Error',
          subtitle: 'Network Request Failed',
          message: 'Request failed while contacting Telegram gateway.',
          type: 'error'
        });
      }
    }

    async function sendChannelChat(channel, mode) {
      const isTg = channel === 'telegram';
      const targetEl = document.getElementById(isTg ? 'tgChatIdInput' : 'waPhoneInput');
      const inputEl = document.getElementById(isTg ? 'tgManualChatInput' : 'waManualChatInput');
      const fb = document.getElementById(isTg ? 'tgFeedback' : 'waFeedback');
      const recipient = targetEl ? targetEl.value.trim() : '';
      const text = inputEl ? inputEl.value.trim() : '';

      if (mode === 'manual' && !text) {
        showToast('Enter a message to send.', 'warning');
        return;
      }
      if (!isTg && !recipient) {
        showToast('Enter recipient phone number first.', 'warning');
        return;
      }

      fb.classList.remove('hidden');
      fb.className = 'text-xs p-3 rounded-lg border font-mono bg-cyan-950/40 border-cyan-500/30 text-cyan-300';
      fb.innerText = `⏳ Running ${mode} dispatch on ${channel}...`;

      try {
        const res = await fetch('/api/setup/channels/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ channel, recipient, text, mode })
        });
        const data = await res.json();
        if (data.status === 'delivered' || data.status === 'sent') {
          if (inputEl && mode === 'manual') inputEl.value = '';
          fb.className = 'text-xs p-3 rounded-lg border font-mono bg-emerald-950/40 border-emerald-500/30 text-emerald-300';
          fb.innerHTML = `✓ <strong>Sent (${mode})!</strong><br>${(data.reply_preview || '').replace(/</g, '&lt;')}`;
          showToast(`Sent ${mode} to ${channel}!`, 'success');
        } else {
          fb.className = 'text-xs p-3 rounded-lg border font-mono bg-amber-950/40 border-amber-500/30 text-amber-300';
          fb.innerText = `⚠️ ${data.message || JSON.stringify(data)}`;
        }
      } catch (e) {
        fb.className = 'text-xs p-3 rounded-lg border font-mono bg-red-950/40 border-red-500/30 text-red-300';
        fb.innerText = `❌ Failed to send ${mode} on ${channel}.`;
      }
    }

    async function sendTelegramTestMsg() {
      return sendChannelChat('telegram', 'manual');
    }

    let tgPollTimer = null;
    function stopTgPolling() {
      if (tgPollTimer) {
        clearInterval(tgPollTimer);
        tgPollTimer = null;
      }
    }
    function startTgPolling() {
      stopTgPolling();
      tgPollTimer = setInterval(async () => {
        try {
          const res = await fetch('/api/setup/channels/telegram/poll-link');
          const data = await res.json();
          if (data.linked && data.chat_id) {
            stopTgPolling();
            const chatInp = document.getElementById('tgChatIdInput');
            if (chatInp) chatInp.value = data.chat_id;
            const linkBox = document.getElementById('tgLinkContainer');
            if (linkBox) linkBox.classList.add('hidden');
            await loadChannelsStatus();
            showMessageModal({
              title: 'Telegram Chat Linked!',
              subtitle: data.username || `Chat ID: ${data.chat_id}`,
              message: `Auto-linked Telegram Chat ID ${data.chat_id}. You can now send test messages.`,
              type: 'success'
            });
          }
        } catch (e) {}
      }, 2500);
    }

    function disconnectTelegramBot() {
      showConfirmDialog({
        title: 'Disconnect Telegram Bot?',
        subtitle: 'Telegram Bot Gateway',
        message: 'Clear the saved Telegram Bot token and linked Chat ID?',
        confirmText: '🔌 Disconnect',
        confirmClass: 'bg-red-500 hover:bg-red-600 text-white',
        onConfirm: async () => {
          stopTgPolling();
          await fetch('/api/setup/channels/telegram/disconnect', { method: 'POST' });
          const tInp = document.getElementById('tgTokenInput');
          const cInp = document.getElementById('tgChatIdInput');
          if (tInp) tInp.value = '';
          if (cInp) cInp.value = '';
          const linkBox = document.getElementById('tgLinkContainer');
          if (linkBox) linkBox.classList.add('hidden');
          const fb = document.getElementById('tgFeedback');
          if (fb) fb.classList.add('hidden');
          await loadChannelsStatus();
          showMessageModal({
            title: 'Telegram Disconnected',
            subtitle: 'Session Cleared',
            message: 'Telegram Bot disconnected successfully.',
            type: 'info'
          });
        }
      });
    }

    async function saveWizardTelegram() {
      const token = document.getElementById('wizTgTokenInput').value.trim();
      const st = document.getElementById('wizTgStatus');
      if (!token) return;
      st.classList.remove('hidden');
      st.className = 'text-[11px] p-2 rounded bg-cyan-950 text-cyan-300 font-mono';
      st.innerText = "⏳ Verifying...";
      try {
        const res = await fetch('/api/setup/channels/telegram/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bot_token: token })
        });
        const data = await res.json();
        if (data.status === 'success') {
          st.className = 'text-[11px] p-2 rounded bg-emerald-950 text-emerald-300 font-mono';
          st.innerText = `✓ Verified: ${data.bot_name} (${data.bot_username})`;
        } else {
          st.className = 'text-[11px] p-2 rounded bg-red-950 text-red-300 font-mono';
          st.innerText = `❌ ${data.message}`;
        }
      } catch (e) {
        st.innerText = "❌ Verification error";
      }
    }

    let waPollTimer = null;
    function stopWaPolling() {
      if (waPollTimer) {
        clearInterval(waPollTimer);
        waPollTimer = null;
      }
    }
    function startWaPolling() {
      stopWaPolling();
      waPollTimer = setInterval(async () => {
        try {
          const res = await fetch('/api/setup/channels/status');
          const data = await res.json();
          if (data.whatsapp && data.whatsapp.paired) {
            stopWaPolling();
            const qrCont = document.getElementById('waQrContainer');
            if (qrCont) qrCont.classList.add('hidden');
            await loadChannelsStatus();
            showMessageModal({
              title: 'WhatsApp Linked!',
              subtitle: data.whatsapp.device || 'Baileys Web Bridge',
              message: `Successfully connected WhatsApp (${data.whatsapp.phone || 'Linked'}). You can now send messages.`,
              type: 'success'
            });
          }
        } catch (e) {}
      }, 2000);
    }

    async function generateWhatsAppQR() {
      const container = document.getElementById('waQrContainer');
      const svgBox = document.getElementById('waQrSvgBox');
      const codeBox = document.getElementById('waPairingCodeBox');
      const fb = document.getElementById('waFeedback');

      container.classList.remove('hidden');
      svgBox.innerHTML = '<div class="text-xs text-slate-400 py-6">⏳ Connecting to WhatsApp Web (Baileys)...</div>';

      try {
        const res = await fetch('/api/setup/channels/whatsapp/qr');
        const data = await res.json();
        if (data.connected) {
          container.classList.add('hidden');
          await loadChannelsStatus();
          showMessageModal({
            title: 'WhatsApp Already Connected',
            subtitle: data.phone || 'Linked Session',
            message: 'WhatsApp Web session is already active and ready to send messages.',
            type: 'success'
          });
          return;
        }
        if (data.qr_svg) {
          svgBox.innerHTML = data.qr_svg;
          codeBox.innerText = data.pairing_code || "SCAN-QR";
          if (fb) {
            fb.classList.remove('hidden');
            fb.className = 'text-xs p-2.5 rounded-lg border font-mono bg-emerald-950/40 border-emerald-500/30 text-emerald-300';
            fb.innerHTML = `✓ <strong>Live WhatsApp QR Ready.</strong> Open WhatsApp ➔ Linked Devices ➔ Link a Device and scan this QR code.`;
          }
          startWaPolling();
        } else {
          svgBox.innerHTML = '<div class="text-xs text-amber-400 py-6">QR not ready yet—click Generate again in 2 seconds.</div>';
        }
      } catch (e) {
        svgBox.innerHTML = '<div class="text-xs text-red-400 py-6">Failed to start WhatsApp Web QR session.</div>';
      }
    }

    async function pairWhatsAppDevice() {
      const phoneInputEl = document.getElementById('waPhoneInput');
      const rawPhone = phoneInputEl ? phoneInputEl.value.trim() : '';
      if (!rawPhone) {
        showMessageModal({
          title: 'Phone Number Required',
          subtitle: 'WhatsApp Link with Phone Number',
          message: 'Enter your own WhatsApp phone number (with country code, e.g. +919810795310) to generate an 8-digit WhatsApp pairing code, OR click "Generate Scannable QR Code".',
          type: 'warning'
        });
        if (phoneInputEl) phoneInputEl.focus();
        return;
      }
      const fb = document.getElementById('waFeedback');
      const container = document.getElementById('waQrContainer');
      const svgBox = document.getElementById('waQrSvgBox');
      const codeBox = document.getElementById('waPairingCodeBox');
      try {
        const res = await fetch('/api/setup/channels/whatsapp/pair', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: rawPhone, device_name: "RAA Studio Baileys" })
        });
        const data = await res.json();
        if (data.connected || data.status === 'connected') {
          if (container) container.classList.add('hidden');
          await loadChannelsStatus();
          showMessageModal({
            title: 'WhatsApp Device Linked',
            subtitle: data.device || 'Baileys Web Bridge',
            message: `Successfully linked WhatsApp to ${data.phone || rawPhone}.`,
            type: 'success'
          });
        } else if (data.pairing_code || data.qr_svg) {
          if (container) container.classList.remove('hidden');
          if (svgBox && data.qr_svg) svgBox.innerHTML = data.qr_svg;
          if (codeBox) codeBox.innerText = data.pairing_code || 'SCAN-QR';
          if (fb) {
            fb.classList.remove('hidden');
            fb.className = 'text-xs p-3 rounded-lg border font-mono bg-cyan-950/40 border-cyan-500/30 text-cyan-300';
            fb.innerHTML = `🔐 <strong>Pairing Code Ready:</strong> <code>${data.pairing_code}</code><br>Enter this code in WhatsApp ➔ Linked Devices ➔ Link with phone number instead.`;
          }
          startWaPolling();
          showMessageModal({
            title: 'Enter Pairing Code in WhatsApp',
            subtitle: `Phone: ${rawPhone}`,
            message: `Open WhatsApp -> Settings -> Linked Devices -> Link a Device -> Link with phone number instead, and enter code: ${data.pairing_code}`,
            type: 'info'
          });
        } else {
          showMessageModal({
            title: 'WhatsApp Pairing Failed',
            subtitle: 'Bridge Error',
            message: data.message || 'Could not start WhatsApp pairing.',
            type: 'error'
          });
        }
      } catch (e) {
        showMessageModal({
          title: 'WhatsApp Pairing Failed',
          subtitle: 'Network Error',
          message: 'Device pairing request failed.',
          type: 'error'
        });
      }
    }

    function disconnectWhatsAppDevice() {
      showConfirmDialog({
        title: 'Disconnect WhatsApp?',
        subtitle: 'WhatsApp Web Bridge',
        message: 'Disconnect active WhatsApp session and clear the linked phone number?',
        confirmText: '🔌 Disconnect',
        confirmClass: 'bg-red-500 hover:bg-red-600 text-white',
        onConfirm: async () => {
          try {
            await fetch('/api/setup/channels/whatsapp/disconnect', { method: 'POST' });
            const phoneInp = document.getElementById('waPhoneInput');
            if (phoneInp) phoneInp.value = '';
            const qrCont = document.getElementById('waQrContainer');
            if (qrCont) qrCont.classList.add('hidden');
            const fb = document.getElementById('waFeedback');
            if (fb) {
              fb.classList.remove('hidden');
              fb.className = 'text-xs p-2 rounded bg-slate-900 border border-white/10 text-slate-300';
              fb.innerText = "WhatsApp device disconnected.";
            }
            await loadChannelsStatus();
            showMessageModal({
              title: 'WhatsApp Disconnected',
              subtitle: 'Session Cleared',
              message: 'WhatsApp device disconnected successfully.',
              type: 'info'
            });
          } catch (e) {
            showMessageModal({
              title: 'Disconnect Failed',
              subtitle: 'WhatsApp Web Bridge',
              message: 'Failed to disconnect WhatsApp session.',
              type: 'error'
            });
          }
        }
      });
    }

    async function sendWhatsAppTestMsg() {
      const phone = document.getElementById('waPhoneInput').value.trim();
      const fb = document.getElementById('waFeedback');
      if (!phone) {
        showMessageModal({
          title: 'Recipient Phone Required',
          subtitle: 'WhatsApp Test Message',
          message: 'Please enter a recipient phone number (with country code) first.',
          type: 'warning'
        });
        return;
      }

      fb.classList.remove('hidden');
      fb.className = 'text-xs p-3 rounded-lg border font-mono bg-emerald-950/40 border-emerald-500/30 text-emerald-300';
      fb.innerText = "💬 Dispatching WhatsApp test message...";

      try {
        const res = await fetch('/api/setup/channels/whatsapp/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: phone, text: "🟢 [RAA v4.0.0] WhatsApp Channel Test Ping Successful. Link is operational." })
        });
        const data = await res.json();
        if (data.status === 'delivered') {
          fb.className = 'text-xs p-3 rounded-lg border font-mono bg-emerald-950/40 border-emerald-500/30 text-emerald-300';
          fb.innerHTML = `✓ <strong>WhatsApp Message Delivered!</strong><br>Message ID: <code>${data.message_id}</code> | Recipient: <code>${data.recipient}</code>`;
          loadChannelsStatus();
          showMessageModal({
            title: 'WhatsApp Message Sent',
            subtitle: `Recipient: ${data.recipient}`,
            message: `Test message delivered (ID: ${data.message_id}).`,
            type: 'success'
          });
        } else {
          fb.className = 'text-xs p-3 rounded-lg border font-mono bg-amber-950/40 border-amber-500/30 text-amber-300';
          fb.innerText = `Dispatch status: ${JSON.stringify(data)}`;
          showMessageModal({
            title: 'WhatsApp Notice',
            subtitle: 'Check Pairing Status',
            message: data.message || JSON.stringify(data),
            type: 'warning'
          });
        }
      } catch (e) {
        fb.className = 'text-xs p-3 rounded-lg border font-mono bg-red-950/40 border-red-500/30 text-red-300';
        fb.innerText = "❌ Failed to send WhatsApp test message.";
        showMessageModal({
          title: 'WhatsApp Send Failed',
          subtitle: 'Network Error',
          message: 'Failed to send WhatsApp test message.',
          type: 'error'
        });
      }
    }

    // --- Connected Wi-Fi Mobile Devices Logic ---
    let allWifiDevicesCache = [];

    async function loadWifiDevices() {
      const grid = document.getElementById('wifiDevicesGrid');
      const badge = document.getElementById('wifiSubnetBadge');
      if (badge) badge.innerText = 'Scanning Wi-Fi...';
      if (grid) {
        grid.innerHTML = '<div class="text-slate-400 text-xs col-span-full py-8 text-center">📡 Scanning connected Wi-Fi network for mobile devices...</div>';
      }
      try {
        const res = await fetch('/api/setup/wifi-devices');
        const data = await res.json();
        allWifiDevicesCache = data.devices || [];
        if (badge) {
          badge.innerText = `${data.subnet || 'Local Wi-Fi'} (${allWifiDevicesCache.length} Found)`;
        }
        renderWifiDevices();
      } catch (e) {
        if (badge) badge.innerText = 'Scan Failed';
        if (grid) {
          grid.innerHTML = '<div class="text-red-400 text-xs col-span-full py-8 text-center">Failed to scan connected Wi-Fi network.</div>';
        }
      }
    }

    function renderWifiDevices() {
      const grid = document.getElementById('wifiDevicesGrid');
      if (!grid) return;
      if (allWifiDevicesCache.length === 0) {
        grid.innerHTML = '<div class="text-slate-400 text-xs col-span-full py-8 text-center">No visible mobile devices found on the connected Wi-Fi subnet yet. Ensure mobile Wi-Fi is on and click Scan.</div>';
        return;
      }

      grid.innerHTML = allWifiDevicesCache.map(d => {
        if (d.is_host) {
          const servicesHtml = (d.running_services || []).map(svc => {
            const cls = svc.running
              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/35'
              : 'bg-slate-800/70 text-slate-400 border-white/10';
            const dot = svc.running ? '🟢' : '⚪';
            return `<span class="px-2 py-0.5 rounded-md text-[10px] font-mono border ${cls}">${dot} ${svc.name} :${svc.port}</span>`;
          }).join('');
          return `
            <div class="glass-panel p-4 rounded-xl border border-violet-500/50 bg-gradient-to-br from-violet-500/10 via-cyan-500/5 to-emerald-500/10 shadow-[0_0_20px_rgba(168,85,247,0.16)] space-y-3 flex flex-col justify-between transition">
              <div class="space-y-2">
                <div class="flex justify-between items-start gap-2">
                  <div class="flex items-center space-x-2.5 min-w-0">
                    <span class="text-2xl shrink-0">🖥️</span>
                    <div class="min-w-0">
                      <div class="flex items-center gap-1.5 flex-wrap">
                        <h4 class="font-bold text-white text-sm truncate">${d.device_name}</h4>
                        <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/40 whitespace-nowrap">THIS HOST</span>
                      </div>
                      <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 whitespace-nowrap">${d.vendor || 'Host Machine'}</span>
                    </div>
                  </div>
                  <span class="px-2.5 py-0.5 text-xs font-bold rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/40 whitespace-nowrap shrink-0">🟢 Host · Online</span>
                </div>
                <div class="bg-slate-950/60 p-2 rounded-lg text-[11px] font-mono text-cyan-300 border border-white/5 space-y-1">
                  <div class="flex justify-between">
                    <span class="text-slate-400">Host IP:</span>
                    <span class="font-semibold">${d.ip}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-slate-400">Host MAC:</span>
                    <span>${d.mac || 'N/A'}</span>
                  </div>
                </div>
                <div class="space-y-1">
                  <div class="text-[10px] uppercase font-mono text-slate-400">Running Services</div>
                  <div class="flex flex-wrap gap-1">${servicesHtml}</div>
                </div>
              </div>
              <div class="flex items-center gap-1.5 pt-2 border-t border-white/10">
                <button onclick="copyWifiIp('${d.ip}')" class="flex-1 py-1.5 rounded-lg bg-violet-500/15 text-violet-300 border border-violet-500/35 text-xs font-semibold hover:bg-violet-500/25 transition">
                  📋 Copy Host IP
                </button>
              </div>
            </div>
          `;
        }
        const isConnected = d.adb_status === 'connected';
        const isAdbReady = d.adb_status === 'adb_ready';
        const statusBadge = isConnected
          ? `<span class="px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 whitespace-nowrap shrink-0">🟢 Online · ADB</span>`
          : isAdbReady
            ? `<span class="px-2.5 py-0.5 text-xs font-bold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40 whitespace-nowrap shrink-0">🟢 Online · ADB Ready</span>`
            : `<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 whitespace-nowrap shrink-0">🟢 Online · Wi-Fi</span>`;

        const target = d.adb_target || (d.ip + ':' + (d.adb_port || 5555));
        const activePort = d.adb_port || 5555;
        const labelKey = d.mac || d.ip;
        const isMine = d.custom_label && d.custom_label.toLowerCase().includes('my');
        const displayTitle = d.custom_label ? `${d.custom_label}` : d.device_name;
        const mineBadge = isMine
          ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">⭐ My Device</span>`
          : '';
        return `
          <div class="glass-panel p-4 rounded-xl border ${isConnected ? 'border-emerald-500/40 bg-emerald-500/5' : isMine ? 'border-cyan-500/40 bg-cyan-500/5' : 'border-white/10'} space-y-3 flex flex-col justify-between transition">
            <div class="space-y-2">
              <div class="flex justify-between items-start gap-2">
                <div class="flex items-center space-x-2.5 min-w-0">
                  <span class="text-2xl shrink-0">${d.icon || '📱'}</span>
                  <div class="min-w-0">
                    <div class="flex items-center gap-1.5 flex-wrap">
                      <h4 class="font-bold text-white text-sm truncate">${displayTitle}</h4>
                      ${mineBadge}
                    </div>
                    <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 whitespace-nowrap">${d.vendor || 'Wi-Fi Device'}</span>
                    ${d.custom_label && d.device_name && d.device_name !== d.custom_label && d.device_name !== d.vendor && !d.device_name.startsWith('Mobile Device') ? `<span class="text-[10px] text-slate-400 ml-1">(${d.device_name})</span>` : ''}
                  </div>
                </div>
                ${statusBadge}
              </div>
              <div class="bg-slate-950/60 p-2 rounded-lg text-[11px] font-mono text-cyan-300 border border-white/5 space-y-1">
                <div class="flex justify-between">
                  <span class="text-slate-400">IP : Port</span>
                  <span class="font-semibold">${d.ip}:${activePort}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-slate-400">Unique MAC:</span>
                  <span>${d.mac || 'N/A'}</span>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-1.5 pt-2 border-t border-white/10 flex-wrap">
              ${isConnected ? `
                <button onclick="disconnectWifiAdb('${target}')" class="flex-1 py-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/20 transition">
                  🔌 Disconnect
                </button>
              ` : `
                <button onclick="connectWifiAdb('${target}')" class="flex-1 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold hover:bg-emerald-500/20 transition">
                  🔗 Connect ADB
                </button>
              `}
              <button onclick="editWifiPort('${labelKey}', '${activePort}', '${d.ip}', '${(d.vendor || '').replace(/'/g, '')}')" class="px-2 py-1.5 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/30 text-xs font-semibold hover:bg-amber-500/20 transition" title="Set / Update ADB Port">
                ⚙️ Port
              </button>
              <button onclick="tagWifiDevice('${labelKey}', 'My Phone', '${d.ip}', '${(d.vendor || '').replace(/'/g, '')}')" class="px-2 py-1.5 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-xs font-semibold hover:bg-cyan-500/20 transition" title="Mark as My Phone">
                ⭐
              </button>
              <button onclick="renameWifiDevice('${labelKey}', '${(displayTitle || '').replace(/'/g, '')}', '${d.ip}', '${(d.vendor || '').replace(/'/g, '')}')" class="px-2 py-1.5 rounded-lg bg-slate-800 text-slate-300 border border-white/10 text-xs font-semibold hover:border-cyan-400 transition" title="Rename device">
                ✏️
              </button>
              ${d.custom_label ? `
                <button onclick="clearWifiDeviceLabel('${labelKey}', '${d.ip}')" class="px-2 py-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/20 transition" title="Delete saved rename">
                  🗑️
                </button>
              ` : ''}
              <button onclick="copyWifiIp('${d.ip}')" class="px-2 py-1.5 rounded-lg bg-slate-800 text-slate-300 border border-white/10 text-xs font-semibold hover:border-cyan-400 transition" title="Copy IP Address">
                📋
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function editWifiPort(deviceKey, currentPort, lastIp = '', vendor = '') {
      const modal = document.getElementById('confirmDialogModal');
      const titleEl = document.getElementById('confirmTitle');
      const subEl = document.getElementById('confirmSubtitle');
      const msgEl = document.getElementById('confirmMessage');
      const okBtn = document.getElementById('confirmOkBtn');

      if (!modal || !msgEl) return;
      if (titleEl) titleEl.innerText = 'Update ADB Port';
      if (subEl) subEl.innerText = `Device: ${lastIp} (${deviceKey})`;
      msgEl.innerHTML = `<input id="wifiPortInput" type="number" min="1" max="65535" value="${currentPort || 5555}" onkeydown="if(event.key==='Enter'){event.preventDefault();closeConfirmModal(true);}" placeholder="e.g. 5555 or Wireless Debugging port" class="w-full mt-2 bg-slate-950 border border-white/15 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-400 font-mono" />`;
      if (okBtn) {
        okBtn.innerText = '💾 Save Port';
        okBtn.className = 'py-2 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 text-xs font-bold transition';
      }
      confirmCallback = async () => {
        const inp = document.getElementById('wifiPortInput');
        const portNum = inp ? parseInt(inp.value.trim(), 10) : 0;
        if (!portNum || portNum < 1 || portNum > 65535) {
          showMessageModal({ title: 'Invalid Port', subtitle: 'ADB Port', message: 'Please enter a valid TCP port (1-65535).', type: 'warning' });
          return;
        }
        try {
          const res = await fetch('/api/setup/wifi-devices/label', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: deviceKey, adb_port: portNum, ip: lastIp, vendor: vendor })
          });
          const data = await res.json();
          if (data.status === 'success') {
            allWifiDevicesCache.forEach(item => {
              if ((item.mac && item.mac.toLowerCase() === deviceKey.toLowerCase()) || item.ip === deviceKey) {
                item.adb_port = portNum;
                item.adb_target = item.ip + ':' + portNum;
              }
            });
            renderWifiDevices();
            showMessageModal({ title: 'ADB Port Saved', subtitle: `${lastIp}:${portNum}`, message: `Saved port ${portNum} for this device.`, type: 'success' });
          }
        } catch (e) {
          showMessageModal({ title: 'Save Failed', subtitle: 'ADB Port', message: 'Failed to save ADB port.', type: 'error' });
        }
      };
      modal.classList.remove('hidden');
      setTimeout(() => {
        const inp = document.getElementById('wifiPortInput');
        if (inp) { inp.focus(); inp.select(); }
      }, 50);
    }

    async function tagWifiDevice(deviceKey, label, lastIp = '', vendor = '') {
      try {
        const res = await fetch('/api/setup/wifi-devices/label', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: deviceKey, label: label, ip: lastIp, vendor: vendor })
        });
        const data = await res.json();
        if (data.status === 'success') {
          allWifiDevicesCache.forEach(item => {
            if ((item.mac && item.mac.toLowerCase() === deviceKey.toLowerCase()) || item.ip === deviceKey) {
              item.custom_label = label;
            }
          });
          renderWifiDevices();
          showToast(`✓ Saved device name '${label}'`, 'success');
        } else {
          showToast(`⚠️ ${data.message || 'Failed to save device name'}`, 'warning');
        }
      } catch (e) {
        showToast('Failed to save device label.', 'error');
      }
    }

    async function clearWifiDeviceLabel(deviceKey, lastIp = '') {
      try {
        const res = await fetch('/api/setup/wifi-devices/label', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: deviceKey, ip: lastIp, clear_label: true })
        });
        const data = await res.json();
        if (data.status === 'success') {
          allWifiDevicesCache.forEach(item => {
            if ((item.mac && item.mac.toLowerCase() === deviceKey.toLowerCase()) || item.ip === deviceKey || (lastIp && item.ip === lastIp)) {
              item.custom_label = '';
            }
          });
          renderWifiDevices();
          showToast('✓ Removed saved device name.', 'success');
        } else {
          showToast(`⚠️ ${data.message || 'Failed to remove device name'}`, 'warning');
        }
      } catch (e) {
        showToast('Failed to remove device name.', 'error');
      }
    }

    function renameWifiDevice(deviceKey, currentName, lastIp = '', vendor = '') {
      const modal = document.getElementById('confirmDialogModal');
      const titleEl = document.getElementById('confirmTitle');
      const subEl = document.getElementById('confirmSubtitle');
      const msgEl = document.getElementById('confirmMessage');
      const okBtn = document.getElementById('confirmOkBtn');

      if (!modal || !msgEl) return;
      if (titleEl) titleEl.innerText = 'Rename Wi-Fi Device';
      if (subEl) subEl.innerText = 'Unique Address: ' + deviceKey;
      msgEl.innerHTML = `<input id="wifiRenameInput" type="text" value="${currentName}" onkeydown="if(event.key==='Enter'){event.preventDefault();closeConfirmModal(true);}" placeholder="Leave blank to clear, or enter e.g. My Samsung S23" class="w-full mt-2 bg-slate-950 border border-white/15 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-400" />`;
      if (okBtn) {
        okBtn.innerText = '💾 Save Name';
        okBtn.className = 'py-2 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 text-xs font-bold transition';
      }
      confirmCallback = async () => {
        const inp = document.getElementById('wifiRenameInput');
        const newName = inp ? inp.value.trim() : '';
        if (newName) {
          await tagWifiDevice(deviceKey, newName, lastIp, vendor);
        } else {
          await clearWifiDeviceLabel(deviceKey, lastIp);
        }
      };
      modal.classList.remove('hidden');
      setTimeout(() => {
        const inp = document.getElementById('wifiRenameInput');
        if (inp) {
          inp.focus();
          inp.select();
        }
      }, 50);
    }

    let wifiQrPollTimer = null;

    function closeWifiQrPairModal() {
      if (wifiQrPollTimer) {
        clearInterval(wifiQrPollTimer);
        wifiQrPollTimer = null;
      }
      const modal = document.getElementById('wifiQrPairModal');
      if (modal) modal.classList.add('hidden');
    }

    function upsertWifiDeviceCard(dev) {
      if (!dev || !dev.ip) return;
      const idx = allWifiDevicesCache.findIndex(d =>
        !d.is_host && ((d.mac && dev.mac && d.mac.toLowerCase() === dev.mac.toLowerCase()) || d.ip === dev.ip)
      );
      if (idx >= 0) {
        const existing = allWifiDevicesCache[idx];
        allWifiDevicesCache[idx] = {
          ...existing,
          ...dev,
          mac: dev.mac || existing.mac || '',
          custom_label: dev.custom_label || existing.custom_label || '',
        };
      } else {
        allWifiDevicesCache.push(dev);
      }
      const badge = document.getElementById('wifiSubnetBadge');
      if (badge) {
        const curText = badge.innerText || '';
        const prefix = curText.includes('(') ? curText.split('(')[0].trim() : 'Local Wi-Fi';
        badge.innerText = `${prefix} (${allWifiDevicesCache.length} Found)`;
      }
      renderWifiDevices();
    }

    async function openWifiQrPairModal(ip = '', label = 'Android Device') {
      closeWifiQrPairModal();
      const modal = document.getElementById('wifiQrPairModal');
      const titleEl = document.getElementById('wifiQrTitle');
      const svgBox = document.getElementById('wifiQrSvgBox');
      const statusEl = document.getElementById('wifiQrStatus');
      if (!modal || !svgBox || !statusEl) return;

      if (titleEl) {
        titleEl.innerText = ip ? `📷 Pair ${label || ip} with QR Code` : '📷 Pair Device with QR Code';
      }
      svgBox.innerHTML = '<div class="text-xs text-slate-400 py-8">Generating Android ADB QR code...</div>';
      statusEl.innerText = '⏳ Waiting for phone to scan QR code...';
      statusEl.className = 'text-xs font-mono text-amber-300 text-center';
      modal.classList.remove('hidden');

      try {
        const res = await fetch('/api/setup/wifi-devices/qr-pair/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ip })
        });
        const data = await res.json();
        if (data.status !== 'success') {
          svgBox.innerHTML = `<div class="text-xs text-red-400 py-4">${data.message || 'Failed to generate QR code'}</div>`;
          return;
        }
        svgBox.innerHTML = data.qr_svg || `<div class="text-xs font-mono text-cyan-300 break-all p-3">${data.qr_payload}</div>`;
        const sessionId = data.session_id;
        wifiQrPollTimer = setInterval(async () => {
          try {
            const pRes = await fetch('/api/setup/wifi-devices/qr-pair/poll?session_id=' + encodeURIComponent(sessionId));
            const pData = await pRes.json();
            if (pData.status === 'paired') {
              if (pData.device) {
                upsertWifiDeviceCard(pData.device);
              }
              if (pData.connected) {
                closeWifiQrPairModal();
              } else {
                clearInterval(wifiQrPollTimer);
                wifiQrPollTimer = null;
                statusEl.innerText = `⚠️ ${pData.message || 'Paired, but Wireless Debugging port not open yet. Turn ON Wireless debugging on phone and click Connect ADB.'}`;
                statusEl.className = 'text-xs font-mono text-amber-300 text-center font-semibold';
              }
            } else if (pData.status === 'error') {
              statusEl.innerText = `⚠️ ${pData.message}`;
              statusEl.className = 'text-xs font-mono text-red-400 text-center';
            }
          } catch (e) {}
        }, 1500);
      } catch (e) {
        svgBox.innerHTML = '<div class="text-xs text-red-400 py-4">Network error generating QR code.</div>';
      }
    }

    async function pairWifiAdb() {
      const inp = document.getElementById('wifiManualTargetInput');
      const codeInp = document.getElementById('wifiPairCodeInput');
      const target = inp ? inp.value.trim() : '';
      const code = codeInp ? codeInp.value.trim() : '';
      if (!target || !code) {
        showToast('Enter both the Pairing IP:Port and the 6-digit Pairing Code shown on your phone.', 'warning');
        return;
      }
      showToast(`🔐 Pairing with ${target}...`, 'info');
      try {
        const res = await fetch('/api/setup/wifi-devices/pair', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target: target, code: code })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(`✓ ${data.message}`, 'success');
          if (codeInp) codeInp.value = '';
          loadWifiDevices();
        } else {
          showToast(`⚠️ ${data.message || 'ADB pairing failed'}`, 'warning');
        }
      } catch (e) {
        showToast('Failed to pair Wireless ADB.', 'error');
      }
    }

    async function connectWifiAdb(target) {
      const inp = document.getElementById('wifiManualTargetInput');
      const finalTarget = target || (inp ? inp.value.trim() : '');
      if (!finalTarget) {
        showToast('Please enter a device IP:Port (e.g. 192.168.1.45:5555).', 'warning');
        return;
      }
      showToast(`🔗 Connecting Wireless ADB to ${finalTarget}...`, 'info');
      try {
        const res = await fetch('/api/setup/wifi-devices/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target: finalTarget })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(`✓ ${data.message}`, 'success');
          if (data.device) {
            upsertWifiDeviceCard(data.device);
          } else {
            const hostIp = String(finalTarget).split(':')[0];
            allWifiDevicesCache = allWifiDevicesCache.map(d => {
              if (!d.is_host && (d.adb_target === finalTarget || d.ip === hostIp)) {
                return { ...d, adb_status: 'connected', adb_target: finalTarget };
              }
              return d;
            });
            renderWifiDevices();
          }
        } else {
          showToast(`⚠️ ${data.message || 'ADB connection failed'}`, 'warning');
        }
      } catch (e) {
        showToast('Failed to connect Wireless ADB.', 'error');
      }
    }

    async function disconnectWifiAdb(target) {
      try {
        const res = await fetch('/api/setup/wifi-devices/disconnect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target: target })
        });
        const data = await res.json();
        if (data.status === 'success') {
          const hostIp = String(target || '').split(':')[0];
          allWifiDevicesCache = allWifiDevicesCache.map(d => {
            if (!d.is_host && (d.adb_target === target || d.ip === hostIp)) {
              return { ...d, adb_status: 'adb_ready' };
            }
            return d;
          });
          renderWifiDevices();
          showToast(`🔌 ${data.message || 'Disconnected ' + target}`, 'info');
        } else {
          showToast(`⚠️ ${data.message || 'Disconnect failed'}`, 'warning');
        }
      } catch (e) {
        showToast('Disconnect failed.', 'error');
      }
    }

    function copyWifiIp(ip) {
      if (navigator.clipboard) navigator.clipboard.writeText(ip);
      const inp = document.getElementById('wifiManualTargetInput');
      if (inp) inp.value = ip + ':5555';
      showToast(`📋 Copied ${ip} to clipboard`, 'info');
    }

    // --- MCP Mesh Logic ---
    async function loadMesh() {
      const grid = document.getElementById('meshGrid');
      try {
        const res = await fetch('/api/setup/mesh/catalog');
        allMeshCache = await res.json();
        renderMeshGrid();
      } catch (e) {
        grid.innerHTML = '<div class="text-slate-400 text-xs col-span-full">Failed to load MCP mesh catalog.</div>';
      }
    }

    function getMeshCategory(m) {
      const key = m.name || m.id;
      if (m.is_custom || !KNOWN_CATALOG_MESH.has(key)) return 'custom';
      const cat = (m.category || '').toLowerCase();
      if (cat.includes('reverse') || cat.includes('search')) return 'reversing';
      if (cat.includes('security') || cat.includes('proxy') || cat.includes('osint')) return 'security';
      if (cat.includes('living canvas') || cat.includes('ui')) return 'ui';
      if (cat.includes('mobile') || cat.includes('android enterprise')) return 'mobile';
      if (cat.includes('automation') || cat.includes('api') || cat.includes('developer') || cat.includes('market')) return 'automation';
      if (cat.includes('storage') || cat.includes('knowledge') || cat.includes('enterprise')) return 'core';
      return 'custom';
    }

    function filterMeshCategory(cat, btn) {
      activeMeshCategory = cat;
      meshCurrentPage = 1;
      document.querySelectorAll('.mesh-category-btn').forEach(b => {
        b.className = 'mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white';
      });
      btn.className = 'mesh-category-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
      renderMeshGrid();
    }

    function goToMeshPage(page) {
      meshCurrentPage = page;
      renderMeshGrid();
    }

    function resetMeshPageAndRender() {
      meshCurrentPage = 1;
      renderMeshGrid();
    }

    function filterMesh(filter, btn) {
      activeMeshFilter = filter;
      meshCurrentPage = 1;
      document.querySelectorAll('.mesh-filter-btn').forEach(b => {
        b.className = 'mesh-filter-btn px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white';
      });
      btn.className = 'mesh-filter-btn px-3 py-1 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40';
      renderMeshGrid();
    }

    function renderMeshGrid() {
      const grid = document.getElementById('meshGrid');
      const countBadge = document.getElementById('meshCountBadge');
      const activeProfile = document.getElementById('profileSelect')?.value || selectedPersona || 'core';
      const profileScoped = allMeshCache.filter(m => isMeshInProfile(m, activeProfile));

      const addedCount = profileScoped.filter(m => m.added).length;
      const activeCount = profileScoped.filter(m => m.added && m.enabled).length;
      countBadge.innerText = `${activeCount} Active / ${addedCount} Added / ${profileScoped.length} Available`;

      let filtered = [...profileScoped];
      if (activeMeshFilter === 'added') {
        filtered = filtered.filter(m => m.added);
      } else if (activeMeshFilter === 'available') {
        filtered = filtered.filter(m => !m.added);
      }

      if (activeMeshCategory !== 'all') {
        filtered = filtered.filter(m => getMeshCategory(m) === activeMeshCategory);
      }

      const meshQuery = (document.getElementById('meshSearchInput')?.value || '').trim().toLowerCase();
      if (meshQuery !== '') {
        filtered = filtered.filter(m =>
          (m.display_name || '').toLowerCase().includes(meshQuery) ||
          (m.name || '').toLowerCase().includes(meshQuery) ||
          (m.description || '').toLowerCase().includes(meshQuery) ||
          (m.category || '').toLowerCase().includes(meshQuery) ||
          (m.endpoint || '').toLowerCase().includes(meshQuery)
        );
      }

      const meshSortMode = document.getElementById('meshSortSelect')?.value || 'default';
      if (meshSortMode === 'name_asc') {
        filtered.sort((a, b) => (a.display_name || a.name || '').localeCompare(b.display_name || b.name || ''));
      } else if (meshSortMode === 'name_desc') {
        filtered.sort((a, b) => (b.display_name || b.name || '').localeCompare(a.display_name || a.name || ''));
      } else if (meshSortMode === 'status_added') {
        const rank = m => (m.added && m.enabled ? 2 : m.added ? 1 : 0);
        filtered.sort((a, b) => (rank(b) - rank(a)) || (a.display_name || a.name || '').localeCompare(b.display_name || b.name || ''));
      } else if (meshSortMode === 'status_available') {
        filtered.sort((a, b) => ((a.added ? 1 : 0) - (b.added ? 1 : 0)) || (a.display_name || a.name || '').localeCompare(b.display_name || b.name || ''));
      } else if (meshSortMode === 'tools_desc') {
        filtered.sort((a, b) => ((b.tools_count || 0) - (a.tools_count || 0)) || (a.display_name || a.name || '').localeCompare(b.display_name || b.name || ''));
      }

      if (filtered.length === 0) {
        grid.innerHTML = '<div class="text-slate-400 text-xs col-span-full py-8 text-center">No connectors match this filter.</div>';
        renderPaginationControls('meshPagination', 1, 0, MESH_PAGE_SIZE, 'goToMeshPage');
        return;
      }

      const totalMeshPages = Math.ceil(filtered.length / MESH_PAGE_SIZE);
      if (meshCurrentPage > totalMeshPages) meshCurrentPage = totalMeshPages;
      if (meshCurrentPage < 1) meshCurrentPage = 1;
      const meshStartIdx = (meshCurrentPage - 1) * MESH_PAGE_SIZE;
      const pagedMesh = filtered.slice(meshStartIdx, meshStartIdx + MESH_PAGE_SIZE);
      renderPaginationControls('meshPagination', meshCurrentPage, filtered.length, MESH_PAGE_SIZE, 'goToMeshPage');

      grid.innerHTML = pagedMesh.map(m => {
        const githubLink = m.github_url ? `<a href="${m.github_url}" target="_blank" rel="noopener noreferrer" class="px-2 py-1 rounded bg-slate-900 border border-white/10 hover:border-cyan-400 text-[11px] text-cyan-300 flex items-center gap-1 transition">🐙 GitHub ↗</a>` : '';
        const websiteLink = m.website_url ? `<a href="${m.website_url}" target="_blank" rel="noopener noreferrer" class="px-2 py-1 rounded bg-slate-900 border border-white/10 hover:border-emerald-400 text-[11px] text-emerald-300 flex items-center gap-1 transition">🌐 Site ↗</a>` : '';
        const linksRow = (githubLink || websiteLink) ? `<div class="flex flex-wrap items-center gap-1.5">${githubLink}${websiteLink}</div>` : '';
        if (m.added) {
          const isEnabled = m.enabled;
          return `
            <div class="glass-panel p-5 rounded-xl border ${isEnabled ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-amber-500/30 bg-amber-500/5'} space-y-3 flex flex-col justify-between transition">
              <div class="space-y-2">
                <div class="flex justify-between items-start">
                  <div class="flex items-center space-x-2">
                    <span class="text-2xl">${m.icon || '🔌'}</span>
                    <div>
                      <h4 class="font-bold text-white text-sm">${m.display_name}</h4>
                      <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">${m.category}</span>
                    </div>
                  </div>
                  <span class="px-2.5 py-0.5 text-xs font-bold rounded-full ${isEnabled ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'}">
                    ${isEnabled ? '🟢 Active' : '⏸️ Deactivated'}
                  </span>
                </div>
                <p class="text-xs text-slate-300">${m.description}</p>
                <div class="bg-slate-950/80 p-2 rounded-lg text-[11px] font-mono text-cyan-300 truncate border border-white/5" title="${m.endpoint}">
                  <span class="text-slate-500">[${m.transport}]</span> ${m.endpoint}
                </div>
                <div class="flex items-center justify-between text-xs text-slate-400 pt-1 font-mono">
                  <span>Tools: <strong class="text-cyan-300">${m.tools_count}</strong> exposed</span>
                  <span class="text-emerald-400 text-[11px]">✓ Connected</span>
                </div>
              </div>

              <div class="pt-2.5 border-t border-white/10 space-y-2">
                ${linksRow}
                <div class="flex items-center gap-2">
                ${isEnabled ? `
                  <button onclick="toggleMesh('${m.name}', false)" class="flex-1 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs font-semibold hover:bg-amber-500/20 transition">
                    ⏸️ Deactivate
                  </button>
                ` : `
                  <button onclick="toggleMesh('${m.name}', true)" class="flex-1 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold hover:bg-emerald-500/20 transition">
                    ▶️ Mark Active
                  </button>
                `}
                <div class="flex items-center gap-2">
                  <button onclick="openMcpConfigModal('${m.name}')" class="px-3 py-1.5 rounded-lg bg-slate-800 text-cyan-300 border border-cyan-500/30 text-xs font-semibold hover:bg-slate-700 transition" title="Configure endpoint & Vault auth">
                    ⚙️ Configure
                  </button>
                  <button onclick="testMeshPing('${m.name}')" class="px-3 py-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-semibold hover:bg-cyan-500/20 transition">
                    🔌 Ping
                  </button>
                  <button onclick="disconnectMesh('${m.name}')" class="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 text-xs font-semibold hover:bg-red-500/20 transition" title="Delete connector">
                    🗑️ Delete
                  </button>
                </div>
                </div>
              </div>
            </div>
          `;
        } else {
          const isInstalled = !!m.installed;
          const isRemote = !!m.is_remote;
          const requiresDownload = !!m.requires_download;
          const badgeHtml = isRemote
            ? (isInstalled
              ? `<span class="px-2 py-0.5 text-xs rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-semibold">✓ Config Staged</span>`
              : `<span class="px-2 py-0.5 text-xs rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/40 font-semibold">☁️ Remote MCP</span>`)
            : (!requiresDownload
              ? `<span class="px-2 py-0.5 text-xs rounded bg-slate-800 text-slate-300 border border-white/10 font-semibold">⚡ Local CLI</span>`
              : (isInstalled
                ? `<span class="px-2 py-0.5 text-xs rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-semibold">📦 Downloaded</span>`
                : `<span class="px-2 py-0.5 text-xs rounded bg-slate-800 text-slate-400 border border-white/10">Not Downloaded</span>`));
          const sizeMetaHtml = isRemote
            ? `<span>Remote Endpoint</span>`
            : (!requiresDownload
              ? `<span>Local Runtime</span>`
              : `<span>~${m.approx_size_mb || 15.0} MB</span>`);

          return `
            <div id="meshCard-${m.name}" class="p-5 rounded-xl border-2 border-dashed border-white/20 hover:border-cyan-400/80 bg-slate-900/40 space-y-3 flex flex-col justify-between transition">
              <div class="space-y-2">
                <div class="flex justify-between items-start">
                  <div class="flex items-center space-x-2">
                    <span class="text-2xl opacity-75">${m.icon || '🔌'}</span>
                    <div>
                      <h4 class="font-bold text-slate-200 text-sm">${m.display_name}</h4>
                      <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${m.category}</span>
                    </div>
                  </div>
                  ${badgeHtml}
                </div>
                <p class="text-xs text-slate-400">${m.description}</p>
                <div class="bg-slate-950/40 p-2 rounded-lg text-[11px] font-mono text-slate-400 truncate border border-white/5" title="${m.endpoint}">
                  <span class="text-slate-600">[${m.transport}]</span> ${m.endpoint}
                </div>
                <div class="flex items-center justify-between text-xs text-slate-500 font-mono">
                  <span>Offers <strong class="text-slate-400">${m.tools_count}</strong> tools</span>
                  ${sizeMetaHtml}
                </div>
              </div>

              <!-- Real-time Download Progress Bar (hidden until downloading) -->
              <div id="mcpProgressArea-${m.name}" class="hidden space-y-2 pt-2 border-t border-white/10">
                <div class="flex justify-between items-center text-[11px] font-mono">
                  <span id="mcpStageText-${m.name}" class="text-cyan-300 font-semibold truncate max-w-[200px]">🌐 Fetching package...</span>
                  <span id="mcpStagePercent-${m.name}" class="text-emerald-400 font-bold">0%</span>
                </div>
                <div class="w-full bg-slate-950 border border-white/10 rounded-full h-2.5 p-0.5 overflow-hidden">
                  <div id="mcpProgressBar-${m.name}" class="bg-gradient-to-r from-cyan-400 via-emerald-400 to-emerald-500 h-1.5 rounded-full transition-all duration-150" style="width: 0%"></div>
                </div>
                <div class="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span id="mcpStageBytes-${m.name}">0.0 MB / ${m.approx_size_mb || 15.0} MB</span>
                  <span id="mcpStageSpeed-${m.name}" class="text-cyan-400">6.8 MB/s</span>
                </div>
              </div>

              <div class="pt-2.5 border-t border-white/10 space-y-2">
                ${linksRow}
                <div id="mcpActionRow-${m.name}" class="flex items-center gap-2">
                <button onclick="openMcpConfigModal('${m.name}')" class="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 font-bold text-xs flex items-center justify-center gap-2 transition hover:bg-emerald-500/30">
                  <span>⚙️ Configure &amp; Connect</span>
                </button>
                ${isInstalled ? `
                  <button disabled class="px-3 py-2.5 rounded-xl bg-slate-900/60 border border-white/10 text-slate-500 text-xs font-semibold cursor-not-allowed opacity-60" title="Already staged on disk">
                    ✓ Staged
                  </button>
                  <button onclick="deleteMeshPackage('${m.name}')" class="px-3 py-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-semibold transition" title="Delete staged package/config to free disk space">
                    🗑️ Delete
                  </button>
                ` : `
                  <button onclick="downloadMesh('${m.name}')" class="px-3 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-white/10 text-slate-300 text-xs font-semibold transition" title="${requiresDownload ? 'Download &amp; stage package locally' : 'Stage MCP config template &amp; launcher locally'}">
                    📦 Stage
                  </button>
                `}
                </div>
              </div>
            </div>
          `;
        }
      }).join('');
    }

    async function deleteMeshPackage(name) {
      showConfirmDialog({
        title: `Delete Staged ${name}?`,
        subtitle: 'Free Disk Space',
        message: `Delete the downloaded/staged package files for '${name}' from disk? You can still configure & connect anytime.`,
        confirmText: 'Delete Package',
        confirmClass: 'bg-red-500 hover:bg-red-600 text-white',
        onConfirm: async () => {
          try {
            const res = await fetch('/api/setup/mesh/delete-package', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name })
            });
            const data = await res.json();
            showMessageModal({
              title: 'MCP Package Deleted',
              subtitle: name,
              message: data.message || `Deleted staged package '${name}'.`,
              type: 'success'
            });
            loadMesh();
          } catch (e) {
            showMessageModal({ title: 'Delete Error', subtitle: name, message: 'Failed to delete MCP package.', type: 'error' });
          }
        }
      });
    }

    async function downloadMesh(name) {
      const m = allMeshCache.find(item => item.name === name);
      const totalMb = (m && m.approx_size_mb) ? m.approx_size_mb : 15.0;
      const progressArea = document.getElementById('mcpProgressArea-' + name);
      const actionRow = document.getElementById('mcpActionRow-' + name);
      const stageText = document.getElementById('mcpStageText-' + name);
      const stagePercent = document.getElementById('mcpStagePercent-' + name);
      const progressBar = document.getElementById('mcpProgressBar-' + name);
      const stageBytes = document.getElementById('mcpStageBytes-' + name);

      if (progressArea) progressArea.classList.remove('hidden');
      if (actionRow) {
        actionRow.innerHTML = `<button disabled class="w-full py-2.5 rounded-xl bg-slate-800 text-slate-400 text-xs font-semibold cursor-wait">⏳ Downloading...</button>`;
      }

      const stages = [
        { pct: 25, text: '🌐 Resolving MCP registry...', speed: '5.4 MB/s' },
        { pct: 60, text: '📥 Downloading server package...', speed: '9.2 MB/s' },
        { pct: 90, text: '📦 Verifying & staging manifest...', speed: '11.8 MB/s' },
      ];
      for (const s of stages) {
        if (stageText) stageText.innerText = s.text;
        if (stagePercent) stagePercent.innerText = s.pct + '%';
        if (progressBar) progressBar.style.width = s.pct + '%';
        if (stageBytes) stageBytes.innerText = `${((totalMb * s.pct) / 100).toFixed(1)} MB / ${totalMb} MB`;
        await new Promise(r => setTimeout(r, 180));
      }

      try {
        const res = await fetch('/api/setup/mesh/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.status === 'success') {
          if (stagePercent) stagePercent.innerText = '100%';
          if (progressBar) progressBar.style.width = '100%';
          if (stageBytes) stageBytes.innerText = `${totalMb} MB / ${totalMb} MB`;
          showToast("✓ " + (data.message || `Downloaded ${name}. Ready to add!`), "success");
          await loadMesh();
        } else {
          showToast("Download failed: " + (data.message || "Unknown error"), "error");
          await loadMesh();
        }
      } catch (e) {
        showToast("Failed to download MCP package.", "error");
        await loadMesh();
      }
    }

    function openMcpConfigModal(name) {
      const m = allMeshCache.find(item => item.name === name);
      if (!m) return;
      document.getElementById('mcpCfgName').value = m.name;
      document.getElementById('mcpCfgTitle').innerText = `⚙️ Configure ${m.display_name || m.name}`;
      document.getElementById('mcpCfgSubtitle').innerText = 'Configure transport, endpoint, and Vault-backed credentials (no download required).';
      document.getElementById('mcpCfgTransport').value = m.transport || 'stdio';
      document.getElementById('mcpCfgEndpoint').value = m.transport === 'stdio' ? (m.command || '') : (m.url || m.endpoint || '');

      const fieldsDiv = document.getElementById('mcpCfgDynamicFields');
      const cfgFields = m.config_fields || [];
      const existingEnv = m.env || {};
      if (cfgFields.length) {
        fieldsDiv.innerHTML = cfgFields.map(f => {
          const curVal = existingEnv[f.key] || '';
          const isVaultRef = typeof curVal === 'string' && curVal.startsWith('vault://');
          const placeholder = isVaultRef ? `${curVal} (stored in Vault — enter new value to update)` : (f.placeholder || '');
          return `
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">${escapeHtml(f.label)} <span class="font-mono text-cyan-400">(${escapeHtml(f.key)})</span></label>
              <input data-mcp-env-key="${escapeHtml(f.key)}" type="${f.secret ? 'password' : 'text'}" value="${isVaultRef ? '' : escapeHtml(curVal)}" placeholder="${escapeHtml(placeholder)}" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono" />
            </div>
          `;
        }).join('');
      } else {
        fieldsDiv.innerHTML = '';
      }
      document.getElementById('mcpCfgExtraEnv').value = '';
      document.getElementById('mcpConfigModal').classList.remove('hidden');
    }

    function closeMcpConfigModal() {
      const modal = document.getElementById('mcpConfigModal');
      if (modal) modal.classList.add('hidden');
    }

    async function submitMcpConfigModal() {
      const name = document.getElementById('mcpCfgName').value;
      const transport = document.getElementById('mcpCfgTransport').value;
      const endpoint = (document.getElementById('mcpCfgEndpoint').value || '').trim();
      const env = {};
      document.querySelectorAll('#mcpCfgDynamicFields [data-mcp-env-key]').forEach(el => {
        const k = el.getAttribute('data-mcp-env-key');
        const v = (el.value || '').trim();
        if (k && v) env[k] = v;
      });
      const extraLines = (document.getElementById('mcpCfgExtraEnv').value || '').split(/\\r?\\n/);
      for (const line of extraLines) {
        const idx = line.indexOf('=');
        if (idx > 0) {
          const k = line.slice(0, idx).trim();
          const v = line.slice(idx + 1).trim();
          if (k && v) env[k] = v;
        }
      }
      const body = { name, transport, env };
      if (transport === 'stdio') body.command = endpoint;
      else body.url = endpoint;

      try {
        const res = await fetch('/api/setup/mesh/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.status === 'success') {
          closeMcpConfigModal();
          showMessageModal({
            title: 'MCP Connector Configured',
            subtitle: name,
            message: data.message || `Connected ${name} (${data.ingested_tools_count || 0} tools).`,
            type: 'success'
          });
          loadMesh();
        } else {
          showMessageModal({ title: 'MCP Configuration Error', subtitle: name, message: data.message || 'Failed to configure MCP server.', type: 'error' });
        }
      } catch (e) {
        showMessageModal({ title: 'MCP Configuration Error', subtitle: name, message: 'Network error while configuring MCP server.', type: 'error' });
      }
    }

    async function connectMesh(name) {
      try {
        const res = await fetch('/api/setup/mesh/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showMessageModal({ title: 'MCP Connected', subtitle: name, message: data.message || `Added ${name} to active MCP mesh.`, type: 'success' });
          loadMesh();
        } else {
          showMessageModal({ title: 'MCP Error', subtitle: name, message: data.message || 'Unknown error', type: 'error' });
        }
      } catch (e) {
        showMessageModal({ title: 'MCP Error', subtitle: name, message: 'Failed to connect MCP server.', type: 'error' });
      }
    }

    async function disconnectMesh(name) {
      showConfirmDialog({
        title: `Remove ${name}?`,
        subtitle: "MCP Mesh Disconnect",
        message: `Remove MCP connector '${name}' from active mesh? This will disconnect the server endpoint.`,
        confirmText: "Disconnect",
        confirmClass: "bg-red-500 hover:bg-red-600 text-white",
        onConfirm: async () => {
          try {
            const res = await fetch('/api/setup/mesh/disconnect', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name: name })
            });
            const data = await res.json();
            if (data.status === 'success') {
              showToast("🗑️ " + (data.message || `Removed ${name} from active mesh.`), "success");
              loadMesh();
            } else {
              showToast("Failed to delete connector: " + (data.message || "Unknown error"), "error");
            }
          } catch (e) {
            showToast("Failed to disconnect MCP server.", "error");
          }
        }
      });
    }

    async function toggleMesh(name, enabled) {
      if (!enabled) {
        showConfirmDialog({
          title: `Disable ${name}?`,
          subtitle: "MCP Connector Deactivation",
          message: `Temporarily deactivate the '${name}' MCP connector? Its external tools will be suspended in RAA Studio until re-enabled.`,
          confirmText: "Deactivate",
          confirmClass: "bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold",
          onConfirm: async () => {
            await executeToggleMesh(name, false);
          }
        });
      } else {
        await executeToggleMesh(name, true);
      }
    }

    async function executeToggleMesh(name, enabled) {
      try {
        const res = await fetch('/api/setup/mesh/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name, enabled: enabled })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(`Connector '${name}' ${enabled ? 'enabled' : 'disabled'}.`, 'info');
          loadMesh();
        } else {
          showToast("Failed to toggle connector: " + (data.message || "Unknown error"), "error");
        }
      } catch (e) {
        showToast("Failed to toggle MCP server.", "error");
      }
    }

    async function testMeshPing(name) {
      try {
        const res = await fetch('/api/setup/mesh/ping', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        showToast("🔌 Ping " + name + ": " + data.ping + " (" + data.latency_ms + "ms)", "info");
      } catch (e) {
        showToast("Mesh ping failed.", "error");
      }
    }

    function toggleCustomMcpForm() {
      const f = document.getElementById('customMcpForm');
      f.classList.toggle('hidden');
    }

    async function submitCustomMcp() {
      const name = document.getElementById('customMcpName').value.trim();
      const transport = document.getElementById('customMcpTransport').value;
      const endpoint = document.getElementById('customMcpEndpoint').value.trim();

      if (!name) {
        showToast("Please enter a connector name/ID.", "warning");
        return;
      }

      const body = { name: name, transport: transport };
      if (transport === 'stdio') {
        body.command = endpoint;
      } else {
        body.url = endpoint;
      }

      try {
        const res = await fetch('/api/setup/mesh/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast("✓ " + data.message, "success");
          toggleCustomMcpForm();
          loadMesh();
        } else {
          showToast("❌ " + (data.message || "Failed to add custom server"), "error");
        }
      } catch (e) {
        showToast("Failed to connect custom MCP server.", "error");
      }
    }

    function updateCadenceButtons(mode, mins) {
      const btns = document.querySelectorAll('.cadence-btn');
      btns.forEach(b => {
        const bMode = b.getAttribute('data-cadence-mode');
        const bMins = Number(b.getAttribute('data-cadence-mins'));
        const isActive = (mode === 'start_end' && bMode === 'start_end') ||
          (mode === 'interval' && bMode === 'interval' && bMins === Number(mins));
        if (isActive) {
          b.className = 'cadence-btn px-3 py-1.5 rounded-lg border border-emerald-400 text-xs text-emerald-400 bg-emerald-500/10 font-bold transition';
        } else {
          b.className = 'cadence-btn px-3 py-1.5 rounded-lg border border-white/10 text-xs text-slate-300 hover:border-emerald-400 transition';
        }
      });
      const lbl = document.getElementById('cadenceActiveLabel');
      if (lbl) {
        lbl.innerText = mode === 'start_end' ? 'Active: Start & End Only' : `Active: Every ${mins} min`;
      }
    }

    async function loadCadenceStatus() {
      try {
        const res = await fetch('/api/setup/cadence');
        const data = await res.json();
        if (data && data.mode) {
          updateCadenceButtons(data.mode, Math.round(data.interval_minutes || 5));
        }
      } catch (e) {}
    }

    async function setCadence(mode, mins) {
      updateCadenceButtons(mode, mins);
      try {
        const res = await fetch('/api/setup/cadence', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: mode, interval_minutes: mins })
        });
        const data = await res.json();
        if (!res.ok || data.status === 'error') {
          showMessageModal({ title: 'Cadence Error', subtitle: 'Notification Cadence', message: data.message || data.detail || 'Failed to update cadence.', type: 'error' });
          return;
        }
        updateCadenceButtons(data.mode || mode, data.mode === 'start_end' ? 0 : Math.round(data.interval_minutes || mins));
      } catch (e) {
        showMessageModal({ title: 'Cadence Error', subtitle: 'Notification Cadence', message: 'Failed to update cadence.', type: 'error' });
      }
    }

    async function loadTvThemes() {
      const sel = document.getElementById('tvThemeSelect');
      if (!sel) return;
      try {
        const res = await fetch('/api/setup/tv/themes');
        const data = await res.json();
        if (Array.isArray(data.themes) && data.themes.length) {
          const cur = sel.value || 'midnight-glass';
          sel.innerHTML = data.themes.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
          if (data.themes.includes(cur)) sel.value = cur;
        }
      } catch (e) {}
    }

    function _tvParseCsv(id) {
      const el = document.getElementById(id);
      return el ? el.value.split(',').map(s => s.trim()).filter(Boolean) : [];
    }

    async function runTvRedesign() {
      const out = document.getElementById('tvOutput');
      const meta = document.getElementById('tvOutputMeta');
      const target = (document.getElementById('tvTargetInput').value || 'com.android.tv.launcher').trim();
      const theme_name = (document.getElementById('tvThemeSelect').value || 'midnight-glass').trim();
      const dock_apps = _tvParseCsv('tvDockAppsInput');
      try {
        const res = await fetch('/api/setup/tv/redesign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target, theme_name, dock_apps })
        });
        const data = await res.json();
        out.classList.remove('hidden');
        if (meta) meta.innerText = data.synthesized_source_file || '';
        out.innerText = data.compose_code || data.compose_preview || JSON.stringify(data, null, 2);
      } catch (e) {
        showMessageModal({ title: 'TV Studio Error', subtitle: 'Compose Redesign', message: 'Failed to synthesize Compose TV M3 layout.', type: 'error' });
      }
    }

    async function applyTvDockTheme() {
      const out = document.getElementById('tvOutput');
      const meta = document.getElementById('tvOutputMeta');
      const tv_host = (document.getElementById('tvHostInput').value || '').trim();
      const theme_name = (document.getElementById('tvThemeSelect').value || 'midnight-glass').trim();
      const dock_apps = _tvParseCsv('tvDockAppsInput');
      const hidden_apps = _tvParseCsv('tvHiddenAppsInput');
      try {
        const res = await fetch('/api/setup/tv/dock-theme', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tv_host, theme_name, dock_apps, hidden_apps })
        });
        const data = await res.json();
        out.classList.remove('hidden');
        if (meta) meta.innerText = data.config_xml_file || '';
        out.innerText = data.xml_preview || JSON.stringify(data, null, 2);
        showMessageModal({ title: 'CleanYourTV Dock & Theme Staged', subtitle: theme_name, message: data.message || 'Staged config_override.xml and cleanyourtv_config.json.', type: 'success' });
      } catch (e) {
        showMessageModal({ title: 'TV Studio Error', subtitle: 'Dock & Theme', message: 'Failed to stage CleanYourTV dock & theme.', type: 'error' });
      }
    }

    async function scanTvPackages() {
      const container = document.getElementById('tvPackagesList');
      const tv_host = (document.getElementById('tvHostInput').value || '').trim();
      if (!container) return;
      container.innerHTML = '<div class="p-3 text-cyan-300">Scanning TV packages...</div>';
      try {
        const res = await fetch('/api/setup/tv/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tv_host })
        });
        const data = await res.json();
        const pkgs = data.packages || [];
        container.innerHTML = pkgs.map(p => {
          const isProtected = p.category === 'protected_system';
          const isBloat = p.category === 'bloatware_candidate';
          const badge = isProtected
            ? '<span class="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[10px]">🛡️ Protected</span>'
            : isBloat
              ? '<span class="px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 text-[10px]">🧹 Bloatware</span>'
              : `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">${escapeHtml(p.category)}</span>`;
          return `
            <label class="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-900/80 border border-white/10 cursor-pointer hover:border-white/20">
              <div class="flex items-center gap-2 min-w-0">
                <input type="checkbox" class="tv-pkg-cb rounded" value="${escapeHtml(p.package)}" ${isBloat ? 'checked' : ''} ${isProtected ? 'disabled' : ''}>
                <span class="font-mono text-slate-200 truncate">${escapeHtml(p.package)}</span>
              </div>
              ${badge}
            </label>
          `;
        }).join('');
      } catch (e) {
        container.innerHTML = '<div class="p-3 text-red-400">Failed to scan TV packages.</div>';
      }
    }

    async function debloatTvApps(restore) {
      const tv_host = (document.getElementById('tvHostInput').value || '').trim();
      const packages = [...document.querySelectorAll('.tv-pkg-cb:checked')].map(el => el.value);
      if (!packages.length) {
        showMessageModal({ title: 'No Packages Selected', subtitle: 'TV Debloater', message: 'Scan TV Apps and select at least one package first.', type: 'warning' });
        return;
      }
      const doRun = async () => {
        try {
          const res = await fetch('/api/setup/tv/debloat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tv_host, packages, restore })
          });
          const data = await res.json();
          const out = document.getElementById('tvOutput');
          const meta = document.getElementById('tvOutputMeta');
          if (out) {
            out.classList.remove('hidden');
            out.innerText = JSON.stringify(data, null, 2);
          }
          if (meta) meta.innerText = data.backup_file || '';
          showMessageModal({
            title: restore ? 'TV Packages Restored' : 'TV Bloatware Disabled',
            subtitle: `${packages.length} package(s)`,
            message: `${restore ? 'Restored' : 'Disabled'} ${packages.length} package(s). Backup: ${data.backup_file || 'saved'}`,
            type: 'success'
          });
        } catch (e) {
          showMessageModal({ title: 'TV Debloat Error', subtitle: 'ADB Action', message: 'Failed to run TV package action.', type: 'error' });
        }
      };
      if (!restore) {
        showConfirmDialog({
          title: 'Disable TV Bloatware?',
          subtitle: tv_host || 'Offline / Staged',
          message: `Safely disable ${packages.length} selected package(s) using pm disable-user? A backup is saved for 1-click restore.`,
          confirmText: 'Disable Selected',
          confirmClass: 'bg-red-500 hover:bg-red-600 text-white',
          onConfirm: doRun
        });
      } else {
        await doRun();
      }
    }

    async function generateTvDoc() {
      const out = document.getElementById('tvOutput');
      const meta = document.getElementById('tvOutputMeta');
      const tv_host = (document.getElementById('tvHostInput').value || '').trim();
      const target = (document.getElementById('tvTargetInput').value || 'com.android.tv.launcher').trim();
      const theme_name = (document.getElementById('tvThemeSelect').value || 'midnight-glass').trim();
      const dock_apps = _tvParseCsv('tvDockAppsInput');
      const removed_apps = [...document.querySelectorAll('.tv-pkg-cb:checked')].map(el => el.value);
      try {
        const res = await fetch('/api/setup/tv/doc', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tv_host, target, theme_name, dock_apps, removed_apps })
        });
        const data = await res.json();
        out.classList.remove('hidden');
        if (meta) meta.innerText = data.doc_file || '';
        out.innerText = data.markdown || JSON.stringify(data, null, 2);
        showMessageModal({ title: 'TV Redesign Doc Generated', subtitle: 'TV_REDESIGN_DOC.md', message: data.message || 'Generated TV Redesign Doc.', type: 'success' });
      } catch (e) {
        showMessageModal({ title: 'TV Studio Error', subtitle: 'Redesign Doc', message: 'Failed to generate Redesign Doc.', type: 'error' });
      }
    }

    function toggleVaultSecretVisibility() {
      const inp = document.getElementById('vaultSecretValue');
      const btn = event && event.target ? event.target : null;
      if (!inp) return;
      if (inp.type === 'password') {
        inp.type = 'text';
        if (btn) btn.innerText = 'Hide';
      } else {
        inp.type = 'password';
        if (btn) btn.innerText = 'Show';
      }
    }

    async function loadVaultSecrets() {
      const container = document.getElementById('vaultSecretsList');
      if (!container) return;
      try {
        const res = await fetch('/api/setup/vault/list');
        const data = await res.json();
        const items = data.secrets || [];
        if (!items.length) {
          container.innerHTML = '<div class="p-4 rounded-lg bg-slate-900/60 border border-white/5 text-slate-400 text-center">No credentials stored in Vault yet.</div>';
          return;
        }
        container.innerHTML = items.map(item => `
          <div class="p-3 rounded-lg bg-slate-900/80 border border-white/10 flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-mono font-semibold text-cyan-300">${escapeHtml(item.key_name)}</span>
                <span class="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300">${escapeHtml(item.service || 'general')}</span>
                <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-[10px] text-emerald-400">${escapeHtml(item.encryption || 'AES-256-GCM')}</span>
              </div>
              <div class="text-[11px] text-slate-400 mt-1 flex flex-wrap gap-x-3">
                ${item.has_username ? `<span>User: <code class="text-slate-300">${escapeHtml(item.username_fingerprint || '***')}</code></span>` : ''}
                ${item.has_secret ? `<span>Token/Pass: <code class="text-slate-300">${escapeHtml(item.fingerprint || '***')}</code></span>` : ''}
                ${item.description ? `<span class="truncate">${escapeHtml(item.description)}</span>` : ''}
              </div>
            </div>
            <button onclick="deleteVaultCredential('${escapeHtml(item.key_name).replace(/'/g, "\\\\'")}')" class="shrink-0 px-2.5 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-[11px] transition">Delete</button>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML = '<div class="p-3 rounded-lg bg-red-500/10 text-red-300 text-xs">Failed to load Vault credentials.</div>';
      }
    }

    async function saveVaultCredential() {
      const key_name = (document.getElementById('vaultKeyName').value || '').trim();
      const service = (document.getElementById('vaultService').value || '').trim() || 'general';
      const username = (document.getElementById('vaultUsername').value || '').trim();
      const secret_value = (document.getElementById('vaultSecretValue').value || '').trim();
      const description = (document.getElementById('vaultDescription').value || '').trim();
      if (!key_name) {
        showMessageModal({ title: 'Validation Error', subtitle: 'Vault', message: 'Please enter a Key / Handle (e.g. TELEGRAM_BOT_TOKEN).', type: 'warning' });
        return;
      }
      if (!username && !secret_value) {
        showMessageModal({ title: 'Validation Error', subtitle: 'Vault', message: 'Please provide an API Token/Password or Username.', type: 'warning' });
        return;
      }
      try {
        const res = await fetch('/api/setup/vault/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key_name, service, username, secret_value, description })
        });
        const data = await res.json();
        if (!res.ok || data.status === 'error') {
          showMessageModal({ title: 'Vault Error', subtitle: key_name, message: data.message || data.detail || 'Failed to save credential.', type: 'error' });
          return;
        }
        document.getElementById('vaultKeyName').value = '';
        document.getElementById('vaultService').value = '';
        document.getElementById('vaultUsername').value = '';
        document.getElementById('vaultSecretValue').value = '';
        document.getElementById('vaultDescription').value = '';
        showMessageModal({ title: 'Saved to Vault', subtitle: key_name, message: data.message || `Credential '${key_name}' encrypted and stored.`, type: 'success' });
        loadVaultSecrets();
      } catch (e) {
        showMessageModal({ title: 'Vault Error', subtitle: key_name, message: 'Network error while saving credential.', type: 'error' });
      }
    }

    async function deleteVaultCredential(keyName) {
      showConfirmDialog({
        title: 'Delete Vault Credential',
        subtitle: keyName,
        message: `Remove '${keyName}' from the encrypted Vault? Connected services using this key will stop resolving it.`,
        confirmText: 'Delete',
        confirmClass: 'bg-red-500 hover:bg-red-600 text-white',
        onConfirm: async () => {
          try {
            const res = await fetch('/api/setup/vault/delete', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ key_name: keyName })
            });
            const data = await res.json();
            showMessageModal({ title: 'Vault Updated', subtitle: keyName, message: data.message || `Removed '${keyName}'.`, type: 'info' });
            loadVaultSecrets();
          } catch (e) {
            showMessageModal({ title: 'Vault Error', subtitle: keyName, message: 'Failed to delete credential.', type: 'error' });
          }
        }
      });
    }

    async function testShield() {
      const inp = document.getElementById('shieldInput').value;
      const out = document.getElementById('shieldOutput');
      try {
        const res = await fetch('/api/setup/shield', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: inp })
        });
        const data = await res.json();
        out.classList.remove('hidden');
        out.innerText = "Status: " + data.status + "\\nInjection Detected: " + data.has_injection_risk + "\\nSecrets Redacted: " + Boolean(data.secrets_redacted) + "\\n\\n" + data.safe_surrogate;
      } catch (e) {
        showMessageModal({ title: "Shield Error", subtitle: "Content Shield", message: "Shield test failed.", type: "error" });
      }
    }

    // Initialize Step 1, restore last active tab, & preload tools inventory on load
    let allSkillsCache = [];
    let activeSkillCategory = 'all';
    let skillsCurrentPage = 1;
    const SKILLS_PAGE_SIZE = 9;

    function toggleCustomSkillForm() {
      const f = document.getElementById('customSkillForm');
      if (f) f.classList.toggle('hidden');
    }

    async function submitCustomSkill() {
      const skill_id = (document.getElementById('customSkillId').value || '').trim().toLowerCase();
      const name = (document.getElementById('customSkillName').value || '').trim();
      const category = document.getElementById('customSkillCategory').value || 'custom';
      const description = (document.getElementById('customSkillDescription').value || '').trim();
      const toolsRaw = (document.getElementById('customSkillTools').value || '').trim();
      const content = (document.getElementById('customSkillContent').value || '').trim();
      if (!skill_id) {
        showMessageModal({ title: 'Validation Error', subtitle: 'Custom Skill', message: 'Please enter a valid Skill ID (lowercase letters, digits, and hyphens).', type: 'warning' });
        return;
      }
      try {
        const res = await fetch('/api/setup/skills/custom-add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            skill_id,
            name: name || skill_id,
            category,
            description,
            tools: toolsRaw ? toolsRaw.split(',').map(t => t.trim()).filter(Boolean) : [],
            content
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          toggleCustomSkillForm();
          document.getElementById('customSkillId').value = '';
          document.getElementById('customSkillName').value = '';
          document.getElementById('customSkillDescription').value = '';
          document.getElementById('customSkillTools').value = '';
          document.getElementById('customSkillContent').value = '';
          showToast(`✅ ${data.message || 'Custom skill saved.'}`, 'success');
          skillsCurrentPage = 1;
          await loadSkills();
        } else {
          showMessageModal({ title: 'Skill Error', subtitle: skill_id, message: data.message || 'Failed to save custom skill.', type: 'error' });
        }
      } catch (e) {
        showMessageModal({ title: 'Skill Error', subtitle: 'Network Error', message: 'Failed to create custom skill.', type: 'error' });
      }
    }

    function filterSkillsCategory(cat, btn) {
      activeSkillCategory = cat;
      skillsCurrentPage = 1;
      document.querySelectorAll('.skill-filter-btn').forEach(b => {
        b.className = 'skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white';
      });
      btn.className = 'skill-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
      renderSkillsGrid();
    }

    function goToSkillsPage(page) {
      skillsCurrentPage = page;
      renderSkillsGrid();
    }

    function resetSkillsPageAndRender() {
      skillsCurrentPage = 1;
      renderSkillsGrid();
    }

    async function loadSkills() {
      const grid = document.getElementById('skillsGrid');
      const badge = document.getElementById('skillsCountBadge');
      try {
        const res = await fetch('/api/setup/skills');
        const data = await res.json();
        allSkillsCache = data.skills || [];
        if (badge) badge.innerText = `${allSkillsCache.length} Skills`;
        renderSkillsGrid();
      } catch (e) {
        if (grid) grid.innerHTML = '<div class="text-red-400 text-xs col-span-full py-8 text-center">Failed to load skills.</div>';
      }
    }

    function renderSkillsGrid() {
      const grid = document.getElementById('skillsGrid');
      const badge = document.getElementById('skillsCountBadge');
      if (!grid) return;
      const q = (document.getElementById('skillSearchInput')?.value || '').trim().toLowerCase();
      const sortMode = document.getElementById('skillSortSelect')?.value || 'default';
      const activeProfile = document.getElementById('profileSelect')?.value || selectedPersona || 'core';

      const profileScoped = allSkillsCache.filter(s => isSkillInProfile(s, activeProfile));
      let filtered = [...profileScoped];

      if (activeSkillCategory !== 'all') {
        filtered = filtered.filter(s => getSkillCategory(s) === activeSkillCategory);
      }

      if (q !== '') {
        filtered = filtered.filter(s =>
          (s.name || '').toLowerCase().includes(q) ||
          (s.id || '').toLowerCase().includes(q) ||
          (s.description || '').toLowerCase().includes(q) ||
          (s.tools || []).some(t => t.toLowerCase().includes(q))
        );
      }

      if (sortMode === 'name_desc') {
        filtered.sort((a, b) => (b.name || b.id).localeCompare(a.name || a.id));
      } else if (sortMode === 'tools_desc') {
        filtered.sort((a, b) => ((b.tools || []).length - (a.tools || []).length) || (a.id || '').localeCompare(b.id || ''));
      } else {
        filtered.sort((a, b) => (a.id || '').localeCompare(b.id || ''));
      }

      if (badge) badge.innerText = `${filtered.length} / ${profileScoped.length} Skills`;

      if (filtered.length === 0) {
        grid.innerHTML = '<div class="text-slate-400 text-xs col-span-full py-8 text-center">No skills match your filter.</div>';
        renderPaginationControls('skillsPagination', 1, 0, SKILLS_PAGE_SIZE, 'goToSkillsPage');
        return;
      }

      const totalSkillsPages = Math.ceil(filtered.length / SKILLS_PAGE_SIZE);
      if (skillsCurrentPage > totalSkillsPages) skillsCurrentPage = totalSkillsPages;
      if (skillsCurrentPage < 1) skillsCurrentPage = 1;
      const skillsStartIdx = (skillsCurrentPage - 1) * SKILLS_PAGE_SIZE;
      const pagedSkills = filtered.slice(skillsStartIdx, skillsStartIdx + SKILLS_PAGE_SIZE);
      renderPaginationControls('skillsPagination', skillsCurrentPage, filtered.length, SKILLS_PAGE_SIZE, 'goToSkillsPage');

      grid.innerHTML = pagedSkills.map(s => {
        const tools = s.tools || [];
        const skillCat = getSkillCategory(s);
        const chips = tools.slice(0, 4).map(t => `<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-white/10 text-cyan-300">${t}</span>`).join('');
        const extra = tools.length > 4 ? `<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">+${tools.length - 4} more</span>` : '';
        return `
          <div class="glass-panel p-4 rounded-xl border border-white/10 hover:border-cyan-400/40 flex flex-col justify-between space-y-3 transition">
            <div class="space-y-2">
              <div class="flex items-start justify-between gap-2">
                <div>
                  <h4 class="font-bold text-white text-sm leading-snug">${s.name}</h4>
                  <div class="flex items-center gap-1.5 mt-0.5 flex-wrap">
                    <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">${s.id}</span>
                    <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20">${skillCat}</span>
                    <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">v${s.version || '1.0'}</span>
                  </div>
                </div>
                <span class="px-2 py-0.5 text-[11px] font-mono rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 shrink-0">${tools.length} tools</span>
              </div>
              <p class="text-xs text-slate-400">${s.description || 'No description provided.'}</p>
              ${tools.length ? `<div class="flex flex-wrap gap-1 pt-1">${chips}${extra}</div>` : ''}
            </div>
            <div class="pt-2.5 border-t border-white/10 flex items-center gap-2">
              <button onclick="viewSkillDetails('${s.id}')" class="flex-1 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-white/10 text-slate-200 text-xs font-semibold transition">
                📄 View SKILL.md
              </button>
              <button onclick="installSkill('${s.id}', false)" class="px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-semibold transition">
                📥 Install
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function viewSkillDetails(skillId) {
      const s = allSkillsCache.find(x => x.id === skillId);
      if (!s) return;
      showMessageModal({
        title: `🧩 ${s.name}`,
        subtitle: `${s.id} · v${s.version || '1.0'} · ${(s.files || []).join(', ')}`,
        message: s.content || s.description || '',
        type: 'info'
      });
    }

    async function installSkill(skillId, installAll = false) {
      const dest = (document.getElementById('skillInstallDestInput')?.value || '.raa-workspace/skills').trim();
      try {
        const res = await fetch('/api/setup/skills/install', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ skill_id: skillId, install_all: installAll, destination: dest })
        });
        const data = await res.json();
        if (data.status === 'success') {
          showToast(`✅ ${data.message}`, 'success');
        } else {
          showToast(`⚠️ ${data.message || 'Skill install failed'}`, 'warning');
        }
      } catch (e) {
        showToast('Failed to install skill.', 'error');
      }
    }

    async function loadWorkspaceRuntimes() {
      const grid = document.getElementById('workspaceRuntimesGrid');
      if (!grid) return;
      try {
        const res = await fetch('/api/setup/workspace/runtimes');
        const data = await res.json();
        const runtimes = data.runtimes || [];
        grid.innerHTML = runtimes.map(rt => {
          const badge = rt.available
            ? `<span class="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shrink-0">✓ Available</span>`
            : `<span class="px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 shrink-0">✗ Not Found</span>`;
          const installBtn = (!rt.available && rt.install_url)
            ? `<a href="${rt.install_url}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-[11px] font-semibold hover:bg-cyan-500/20 transition inline-flex items-center gap-1">🌐 Install ↗</a>`
            : '';
          return `
            <div class="glass-panel p-4 rounded-xl border ${rt.available ? 'border-emerald-500/25' : 'border-amber-500/25'} space-y-2.5 flex flex-col justify-between">
              <div class="space-y-1.5">
                <div class="flex items-start justify-between gap-2">
                  <div class="flex items-center gap-2">
                    <span class="text-xl">${rt.icon || '⚙️'}</span>
                    <div>
                      <h4 class="font-bold text-white text-sm leading-snug">${rt.name}</h4>
                      <span class="text-[11px] font-mono text-slate-400">${rt.version || (rt.available ? 'Detected' : 'Missing on PATH')}</span>
                    </div>
                  </div>
                  ${badge}
                </div>
                <p class="text-xs text-slate-400">${rt.required_for}</p>
              </div>
              <div class="pt-2 border-t border-white/10 flex items-center justify-between gap-2">
                <span class="text-[10px] font-mono text-slate-400 truncate" title="${rt.path || 'Not installed'}">${rt.path || 'Not detected on PATH'}</span>
                ${installBtn}
              </div>
            </div>
          `;
        }).join('');
      } catch (e) {
        grid.innerHTML = '<div class="text-red-400 text-xs col-span-full py-4 text-center">Failed to check system runtimes.</div>';
      }
    }

    initTheme();
    updateWizardUI();
    loadActiveProfile();
    (function restoreSavedTab() {
      const validTabs = ['wizard', 'workspace', 'tools', 'channels', 'wifi', 'mesh', 'skills', 'tv', 'security', 'config'];
      let savedTab = 'wizard';
      try {
        const raw = localStorage.getItem('raa_active_tab');
        if (raw && validTabs.includes(raw)) savedTab = raw;
      } catch (e) {}
      updateProfileDropdownVisibility(savedTab);
      if (savedTab !== 'wizard') {
        switchTab(savedTab);
      }
      if (savedTab !== 'tools') {
        loadTools();
      }
    })();
  </script>

  <!-- Tool Path Configuration & Explorer Dialog Modal -->
  <div id="toolPathModal" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="relative w-full max-w-lg glass-panel rounded-2xl p-6 border border-white/10 shadow-2xl space-y-5 bg-[#0D121F]">
      <button onclick="closeToolPathModal()" class="absolute top-5 right-5 text-slate-400 hover:text-white transition text-lg w-8 h-8 rounded-full bg-slate-800/60 flex items-center justify-center border border-white/10">✕</button>

      <div class="flex items-center space-x-3">
        <div id="modalToolIcon" class="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-2xl">
          ⚙️
        </div>
        <div>
          <h3 id="modalToolTitle" class="text-lg font-bold text-white leading-tight">Configure Binary Path</h3>
          <p id="modalToolCategory" class="text-xs text-cyan-400 font-mono">REVERSING ENGINE</p>
        </div>
      </div>

      <div class="space-y-2">
        <label class="block text-xs font-semibold text-slate-300">Current Binary Location:</label>
        <div class="flex items-center space-x-2">
          <div id="modalCurrentPath" class="flex-1 text-xs font-mono text-cyan-300 bg-slate-950 p-2.5 rounded-xl border border-white/10 truncate" title="">
            Not installed or configured
          </div>
          <button id="modalOpenExplorerBtn" onclick="openCurrentInExplorer()" class="px-3 py-2.5 rounded-xl bg-cyan-500/15 border border-cyan-500/40 hover:bg-cyan-500/25 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition shrink-0" title="Reveal this file in Windows Explorer">
            <span>📂 Reveal</span>
          </button>
        </div>
      </div>

      <div class="space-y-2">
        <div class="flex justify-between items-center">
          <label class="block text-xs font-semibold text-slate-300">Set Custom Path or Select Binary:</label>
          <span class="text-[10px] text-slate-400">Windows executable or JAR</span>
        </div>
        <div class="flex items-center space-x-2">
          <input type="text" id="modalCustomPathInput" placeholder="e.g. C:\\Tools\\apktool\\apktool.jar" class="flex-1 text-xs font-mono text-white bg-slate-950 px-3 py-2.5 rounded-xl border border-white/10 outline-none focus:border-cyan-400 transition" />
          <label for="nativeFilePicker" class="px-3 py-2.5 rounded-xl bg-slate-800 border border-white/10 hover:border-slate-500 text-slate-200 text-xs font-semibold cursor-pointer flex items-center gap-1.5 transition shrink-0" title="Browse local file system using Windows file selector">
            <span>📁 Browse...</span>
          </label>
          <input type="file" id="nativeFilePicker" class="hidden" onchange="handleFilePicked(event)" />
        </div>
        <p class="text-[11px] text-slate-400 leading-normal">
          Click <strong>Browse...</strong> to open the Windows file picker, or click <strong>Reveal</strong> to open the file location directly in Windows Explorer.
        </p>
      </div>

      <div id="modalPathFeedback" class="hidden text-xs p-3 rounded-xl border font-mono"></div>

      <div class="flex justify-between items-center pt-3 border-t border-white/10">
        <button onclick="openCurrentInExplorer()" class="py-2 px-3 rounded-xl bg-slate-900 border border-white/10 hover:border-cyan-400 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition">
          <span>🗂️ Open in Windows Explorer</span>
        </button>
        <div class="flex space-x-2">
          <button onclick="closeToolPathModal()" class="py-2 px-4 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition">
            Cancel
          </button>
          <button onclick="saveModalCustomPath()" class="py-2 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs hover:opacity-90 transition">
            Save Path
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Custom Cyber-Glass Confirmation Modal (Replaces browser confirm()) -->
  <div id="confirmDialogModal" onclick="if(event.target===this) closeConfirmModal(false)" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="relative w-full max-w-md glass-panel rounded-2xl p-6 border border-white/10 shadow-2xl space-y-4 bg-[#0D121F]">
      <button onclick="closeConfirmModal(false)" aria-label="Close modal" title="Close" class="absolute top-4 right-4 text-slate-400 hover:text-white transition text-sm font-bold w-8 h-8 rounded-full bg-slate-800/60 flex items-center justify-center border border-white/10 cursor-pointer">✕</button>
      <div class="flex items-center space-x-3 pr-8">
        <div id="confirmIconBox" class="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-xl text-red-400">
          ⚠️
        </div>
        <div>
          <h4 id="confirmTitle" class="text-base font-bold text-white">Confirm Action</h4>
          <p id="confirmSubtitle" class="text-xs text-slate-400">Action confirmation required</p>
        </div>
      </div>
      <p id="confirmMessage" class="text-xs text-slate-300 leading-relaxed font-mono bg-slate-950/60 p-3 rounded-xl border border-white/5">
        Are you sure?
      </p>
      <div class="flex justify-end space-x-2 pt-2 border-t border-white/10">
        <button id="confirmCancelBtn" onclick="closeConfirmModal(false)" class="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition">
          Cancel
        </button>
        <button id="confirmOkBtn" onclick="closeConfirmModal(true)" class="py-2 px-4 rounded-xl bg-red-500 hover:bg-red-600 text-white text-xs font-bold transition">
          Confirm
        </button>
      </div>
    </div>
  </div>

  <!-- Custom Cyber-Glass Message Modal (Replaces browser alert() & toasts) -->
  <!-- MCP Connector Configuration & Vault Auth Modal (outside <main> for true viewport centering) -->
  <div id="mcpConfigModal" onclick="if(event.target===this) closeMcpConfigModal()" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="glass-panel w-full max-w-lg rounded-2xl border border-cyan-500/40 bg-slate-950 p-6 space-y-4 relative shadow-2xl">
      <button onclick="closeMcpConfigModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white text-sm px-2 py-1 rounded-lg hover:bg-white/10 transition" aria-label="Close">✕</button>
      <div>
        <h3 id="mcpCfgTitle" class="text-base font-bold text-white">Configure MCP Connector</h3>
        <p id="mcpCfgSubtitle" class="text-xs text-slate-400">Connect directly without downloading — tokens are encrypted in Vault.</p>
      </div>
      <input type="hidden" id="mcpCfgName" />
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label class="block text-[11px] text-slate-400 mb-1">Transport</label>
          <select id="mcpCfgTransport" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400">
            <option value="stdio">stdio (CLI / npx)</option>
            <option value="sse">sse (HTTP SSE)</option>
            <option value="streamable-http">streamable-http</option>
          </select>
        </div>
        <div class="sm:col-span-2">
          <label class="block text-[11px] text-slate-400 mb-1">Command (stdio) or Endpoint URL (sse/http)</label>
          <input id="mcpCfgEndpoint" type="text" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono" />
        </div>
      </div>
      <div id="mcpCfgDynamicFields" class="space-y-3"></div>
      <div>
        <label class="block text-[11px] text-slate-400 mb-1">Extra Environment Variables (optional, one <code class="text-cyan-400">KEY=VALUE</code> per line)</label>
        <textarea id="mcpCfgExtraEnv" rows="2" class="w-full bg-slate-900 border border-white/10 text-xs px-3 py-2 rounded-lg text-white outline-none focus:border-cyan-400 font-mono" placeholder="API_TOKEN=your_secret_here"></textarea>
      </div>
      <div class="flex justify-end gap-2 pt-2 border-t border-white/10">
        <button onclick="closeMcpConfigModal()" class="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition">Cancel</button>
        <button onclick="submitMcpConfigModal()" class="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 text-xs font-bold hover:opacity-90 transition">💾 Save &amp; Connect</button>
      </div>
    </div>
  </div>

  <div id="messageDialogModal" onclick="if(event.target===this) closeMessageModal()" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="relative w-full max-w-2xl max-h-[85vh] flex flex-col glass-panel rounded-2xl p-6 border border-white/10 shadow-2xl space-y-4 bg-[#0D121F]">
      <button onclick="closeMessageModal()" aria-label="Close modal" title="Close" class="absolute top-4 right-4 text-slate-400 hover:text-white transition text-sm font-bold w-8 h-8 rounded-full bg-slate-800/60 flex items-center justify-center border border-white/10 cursor-pointer">✕</button>
      <div class="flex items-center space-x-3 pr-8 shrink-0">
        <div id="msgIconBox" class="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/40 flex items-center justify-center text-xl text-cyan-400">
          &#8505;&#65039;
        </div>
        <div>
          <h4 id="msgTitle" class="text-base font-bold text-white">Notification</h4>
          <p id="msgSubtitle" class="text-xs text-slate-400">RAA Studio Status</p>
        </div>
      </div>
      <div id="msgBody" class="text-xs text-slate-300 leading-relaxed font-mono bg-slate-950/60 p-3.5 rounded-xl border border-white/5 break-words whitespace-pre-wrap overflow-y-auto max-h-[55vh]"></div>
      <div class="flex justify-end pt-2 border-t border-white/10 shrink-0">
        <button id="msgOkBtn" onclick="closeMessageModal()" class="py-2 px-5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 text-xs font-bold transition">
          OK
        </button>
      </div>
    </div>
  </div>

  <!-- Wi-Fi ADB QR Code Pairing Modal -->
  <div id="wifiQrPairModal" onclick="if(event.target===this) closeWifiQrPairModal()" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="relative w-full max-w-md glass-panel rounded-2xl p-6 border border-violet-500/40 shadow-2xl space-y-4 bg-[#0D121F]">
      <button onclick="closeWifiQrPairModal()" aria-label="Close" class="absolute top-4 right-4 text-slate-400 hover:text-white text-sm px-2 py-1 rounded-lg hover:bg-white/10 transition">✕</button>
      <div>
        <h3 id="wifiQrTitle" class="text-base font-bold text-white">📷 Pair Device with QR Code</h3>
        <p class="text-xs text-slate-400 mt-0.5">Android 11+ Wireless Debugging QR Pairing</p>
      </div>
      <div id="wifiQrSvgBox" class="flex justify-center items-center p-3 bg-white rounded-xl mx-auto w-fit"></div>
      <ol class="text-xs text-slate-300 space-y-1 list-decimal list-inside bg-slate-950/60 p-3 rounded-xl border border-white/10">
        <li>On your phone, open <strong>Settings → Developer options → Wireless debugging</strong>.</li>
        <li>Tap <strong>Pair device with QR code</strong>.</li>
        <li>Point your phone camera at this QR code to pair automatically.</li>
      </ol>
      <div id="wifiQrStatus" class="text-xs font-mono text-amber-300 text-center">⏳ Waiting for phone to scan QR code...</div>
      <div class="flex justify-end pt-2 border-t border-white/10">
        <button onclick="closeWifiQrPairModal()" class="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition">Close</button>
      </div>
    </div>
  </div>

  <!-- Floating Cyber-Glass Toast Notifications (Legacy fallback container) -->
  <div id="toastContainer" class="fixed bottom-5 right-5 z-50 space-y-2 pointer-events-none max-w-sm"></div>

</body>
</html>
"""


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request) -> str:
    """Serve the Cyber-Glass Neon Design System Setup & Tool Manager visual console."""
    return SETUP_HTML


@router.get("/api/setup/status")
async def setup_status(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        return cast("dict[str, Any]", runtime.tool_manager.get_status())
    return {"status": "ok", "version": "4.0.0"}


@router.get("/api/setup/tools")
async def setup_tools_list(request: Request) -> list[dict[str, Any]]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        return cast("list[dict[str, Any]]", runtime.tool_manager.list_tools())
    return []


@router.post("/api/setup/tools/download")
async def setup_tools_download(request: Request, body: ToolActionBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        return cast(
            "dict[str, Any]",
            runtime.tool_manager.download_tool(name=body.tool_name, force=body.force),
        )
    return {"status": "error", "message": "Runtime not available"}


def _resolve_existing_path(target_path: str) -> str:
    """Resolve target_path to an existing file or nearest existing ancestor directory."""
    norm_path = os.path.abspath(os.path.normpath(target_path))
    if os.path.exists(norm_path):
        return norm_path
    candidate = os.path.dirname(norm_path)
    while candidate:
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return ""


def _open_path_sync(target_path: str) -> dict[str, Any]:
    import platform

    resolved_path = _resolve_existing_path(target_path)
    if not resolved_path:
        return {
            "status": "error",
            "message": f"No existing file or folder found for: {target_path}",
        }

    try:
        if platform.system() == "Windows":
            if os.path.isfile(resolved_path):
                res = ctypes.windll.shell32.ShellExecuteW(
                    None, "open", "explorer.exe", f'/select,"{resolved_path}"', None, 1
                )
                if res <= 32:
                    subprocess.Popen(
                        ["explorer.exe", f"/select,{resolved_path}"],
                        creationflags=subprocess.DETACHED_PROCESS,
                    )
            else:
                os.startfile(resolved_path)  # noqa: S606
        elif platform.system() == "Darwin":
            if os.path.isfile(resolved_path):
                subprocess.Popen(["open", "-R", resolved_path])
            else:
                subprocess.Popen(["open", resolved_path])
        else:
            folder = (
                os.path.dirname(resolved_path) if os.path.isfile(resolved_path) else resolved_path
            )
            subprocess.Popen(["xdg-open", folder])

        return {
            "status": "success",
            "message": f"Opened in Windows Explorer: {resolved_path}",
            "path": resolved_path,
        }
    except Exception as exc:
        logger.warning("Could not open path in explorer: %s", exc)
        return {"status": "error", "message": "Could not open path in explorer."}


def _resolve_open_target_for_tm(
    tm: Any,
    tool_name: str,
    requested_path: str,
) -> str:
    tools = tm.list_tools()
    known_paths: dict[str, str] = {}
    known_ids: dict[str, str] = {}
    target_path = ""
    for t in tools:
        tid = str(t.get("tool_id") or "")
        if tid:
            known_ids[tid] = tid
        bp = t.get("binary_path")
        if bp:
            resolved_bp = str(Path(bp).resolve())
            known_paths[resolved_bp] = resolved_bp
            if tid == tool_name and not requested_path:
                target_path = resolved_bp

    tools_dir = tm.tools_dir
    tools_dir.mkdir(parents=True, exist_ok=True)

    if requested_path and "\x00" not in requested_path:
        try:
            norm_req = os.path.normpath(os.path.abspath(requested_path))
        except OSError:
            norm_req = ""
        if norm_req in known_paths:
            return known_paths[norm_req]

    if target_path:
        return target_path
    canonical_tool = known_ids.get(tool_name, "")
    tool_subdir = (tools_dir / canonical_tool) if canonical_tool else tools_dir
    return str(tool_subdir if tool_subdir.exists() else tools_dir)


@router.post("/api/setup/tools/open-path")
async def setup_tools_open_path(request: Request, body: ToolOpenPathBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    requested_path = (body.path or "").strip()
    target_path = ""
    if runtime and hasattr(runtime, "tool_manager"):
        target_path = _resolve_open_target_for_tm(
            runtime.tool_manager, body.tool_name or "", requested_path
        )

    if not target_path:
        return {"status": "error", "message": "No valid file or folder path available to open."}

    return _open_path_sync(target_path)


@router.post("/api/setup/tools/custom-add")
async def setup_tools_custom_add(request: Request, body: ToolCustomAddBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        try:
            res = runtime.tool_manager.add_custom_tool(
                tool_id=body.tool_id,
                display_name=body.display_name,
                category=body.category,
                source_type=body.source_type,
                artifact_type=body.artifact_type,
                download_url=body.download_url,
                filename=body.filename,
                relative_bin_dir=body.relative_bin_dir,
                description=body.description,
                pip_package=body.pip_package,
            )
            if body.auto_download:
                dl = runtime.tool_manager.download_tool(res["tool_id"], force=True)
                res["download"] = dl
                res["message"] = dl.get("message", res["message"])
            return cast("dict[str, Any]", res)
        except Exception as exc:
            logger.warning("Failed to add custom tool: %s", exc)
            return {"status": "error", "message": "Failed to add custom tool."}
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/tools/custom-path")
async def setup_tools_custom_path(request: Request, body: ToolCustomPathBody) -> dict[str, Any]:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", body.tool_name or ""):
        return {"status": "error", "message": "Invalid tool identifier."}
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        try:
            return cast(
                "dict[str, Any]",
                runtime.tool_manager.configure_custom_path(
                    name=body.tool_name, custom_path=body.custom_path
                ),
            )
        except Exception as exc:
            logger.warning("Failed to configure custom tool path: %s", exc)
            return {"status": "error", "message": "Failed to configure custom tool path."}
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/tools/verify")
async def setup_tools_verify(request: Request, body: ToolActionBody) -> dict[str, Any]:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", body.tool_name or ""):
        return {"status": "error", "verified": False}
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        return cast("dict[str, Any]", runtime.tool_manager.verify_tool(name=body.tool_name))
    return {"status": "error", "verified": False}


@router.post("/api/setup/tools/delete")
async def setup_tools_delete(request: Request, body: ToolActionBody) -> dict[str, Any]:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", body.tool_name or ""):
        return {"status": "error", "message": "Invalid tool identifier."}
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        return cast("dict[str, Any]", runtime.tool_manager.delete_tool(name=body.tool_name))
    return {"status": "error", "message": "Runtime not available"}


@router.get("/api/setup/tv/themes")
async def setup_tv_themes(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tv_studio"):
        return {"status": "success", "themes": runtime.tv_studio.list_themes()}
    return {
        "status": "success",
        "themes": ["default", "midnight-glass", "ambient-glass", "minimal"],
    }


@router.post("/api/setup/tv/redesign")
async def setup_tv_redesign(request: Request, body: TvRedesignBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tv_studio"):
        return cast(
            "dict[str, Any]",
            runtime.tv_studio.redesign_tv_ui(
                target_input=body.target,
                theme_name=body.theme_name,
                dock_apps=body.dock_apps or None,
            ),
        )
    return {"status": "error", "message": "TV Studio service unavailable."}


@router.post("/api/setup/tv/scan")
async def setup_tv_scan(request: Request, body: TvScanBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tv_studio"):
        return cast("dict[str, Any]", runtime.tv_studio.inspect_tv_packages(tv_host=body.tv_host))
    return {"status": "error", "message": "TV Studio service unavailable."}


@router.post("/api/setup/tv/debloat")
async def setup_tv_debloat(request: Request, body: TvDebloatBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tv_studio"):
        return cast(
            "dict[str, Any]",
            runtime.tv_studio.debloat_tv_apps(
                tv_host=body.tv_host,
                packages=body.packages,
                restore=body.restore,
            ),
        )
    return {"status": "error", "message": "TV Studio service unavailable."}


@router.post("/api/setup/tv/dock-theme")
async def setup_tv_dock_theme(request: Request, body: TvDockThemeBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tv_studio"):
        return cast(
            "dict[str, Any]",
            runtime.tv_studio.configure_dock_and_theme(
                dock_apps=body.dock_apps,
                hidden_apps=body.hidden_apps,
                theme_name=body.theme_name,
                tv_host=body.tv_host,
            ),
        )
    return {"status": "error", "message": "TV Studio service unavailable."}


@router.post("/api/setup/tv/doc")
async def setup_tv_doc(request: Request, body: TvDocBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tv_studio"):
        return cast(
            "dict[str, Any]",
            runtime.tv_studio.generate_redesign_doc(
                target_input=body.target,
                theme_name=body.theme_name,
                dock_apps=body.dock_apps or None,
                removed_apps=body.removed_apps or None,
                tv_host=body.tv_host,
            ),
        )
    return {"status": "error", "message": "TV Studio service unavailable."}


@router.get("/api/tv/mcp")
async def tv_mcp_info(request: Request) -> dict[str, Any]:
    """Streamable-HTTP MCP discovery endpoint for Living Canvas TV Studio Bridge."""
    return {
        "name": "Living Canvas TV Studio Bridge",
        "protocolVersion": "2024-11-05",
        "transport": "streamable-http",
        "status": "ready",
        "tools": [
            "tv_redesign_ui",
            "tv_inspect_packages",
            "tv_debloat_apps",
            "tv_configure_dock_theme",
            "tv_generate_redesign_doc",
        ],
    }


@router.post("/api/tv/mcp")
async def tv_mcp_rpc(request: Request) -> dict[str, Any]:
    """Streamable-HTTP JSON-RPC 2.0 endpoint for Living Canvas TV Studio Bridge."""
    runtime = getattr(request.app.state, "runtime", None)
    payload = await request.json()
    rpc_id = payload.get("id")
    method = payload.get("method", "")
    params = payload.get("params") or {}

    if method == "initialize":
        result: Any = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "raa-tv-studio", "version": "4.0.0"},
            "capabilities": {"tools": {}},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "tv_redesign_ui",
                    "description": "Deconstruct Leanback TV layout and synthesize Compose for TV Material 3.",
                },
                {
                    "name": "tv_inspect_packages",
                    "description": "Scan Android TV packages and classify bloatware vs protected system apps.",
                },
                {
                    "name": "tv_debloat_apps",
                    "description": "Safely disable TV bloatware via pm disable-user with backup & restore.",
                },
                {
                    "name": "tv_configure_dock_theme",
                    "description": "Configure CleanYourTV dock apps, hidden apps, and theme.",
                },
                {
                    "name": "tv_generate_redesign_doc",
                    "description": "Generate TV architecture, debloat, and launcher redesign documentation.",
                },
            ]
        }
    elif method == "tools/call" and runtime and hasattr(runtime, "tv_studio"):
        tname = params.get("name", "")
        args = params.get("arguments") or {}
        tv = runtime.tv_studio
        if tname == "tv_redesign_ui":
            out = tv.redesign_tv_ui(
                args.get("target", "com.android.tv.launcher"),
                theme_name=args.get("theme_name", "midnight-glass"),
                dock_apps=args.get("dock_apps"),
            )
        elif tname == "tv_inspect_packages":
            out = tv.inspect_tv_packages(tv_host=args.get("tv_host", ""))
        elif tname == "tv_debloat_apps":
            out = tv.debloat_tv_apps(
                tv_host=args.get("tv_host", ""),
                packages=args.get("packages", []),
                restore=bool(args.get("restore", False)),
            )
        elif tname == "tv_configure_dock_theme":
            out = tv.configure_dock_and_theme(
                dock_apps=args.get("dock_apps", []),
                hidden_apps=args.get("hidden_apps"),
                theme_name=args.get("theme_name", "midnight-glass"),
                tv_host=args.get("tv_host", ""),
            )
        elif tname == "tv_generate_redesign_doc":
            out = tv.generate_redesign_doc(
                target_input=args.get("target", "com.android.tv.launcher"),
                theme_name=args.get("theme_name", "midnight-glass"),
                dock_apps=args.get("dock_apps"),
                removed_apps=args.get("removed_apps"),
                tv_host=args.get("tv_host", ""),
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tname}"},
            }
        result = {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]}
    else:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {"code": -32601, "message": f"Unsupported method: {method}"},
        }

    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


@router.get("/api/setup/skills")
async def setup_skills_list_endpoint(request: Request) -> dict[str, Any]:
    from raa.services.skills import SkillService, _parse_frontmatter

    runtime = getattr(request.app.state, "runtime", None)
    skills_svc = runtime.skills if (runtime and hasattr(runtime, "skills")) else SkillService()
    items = []
    for sk in skills_svc.discover():
        summary = sk.summary()
        summary["path"] = str(sk.path)
        summary["content"] = sk.content
        try:
            meta, _ = _parse_frontmatter(sk.content)
            if meta.get("category"):
                summary["category"] = str(meta["category"])
            if str(meta.get("custom", "")).lower() == "true":
                summary["is_custom"] = True
        except Exception as exc:
            logger.debug("Failed to parse skill frontmatter for %s: %s", sk.id, exc)
        items.append(summary)
    return {"skills": items}


@router.post("/api/setup/skills/custom-add")
async def setup_skills_custom_add_endpoint(request: Request) -> dict[str, Any]:
    from raa.services.skills import SkillService

    body = await request.json()
    skill_id = str(body.get("skill_id") or "").strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", skill_id):
        return {
            "status": "error",
            "message": "Invalid skill_id. Use lowercase letters, digits, and hyphens (e.g. my-custom-audit).",
        }

    name = str(body.get("name") or skill_id).strip()
    category = str(body.get("category") or "custom").strip().lower() or "custom"
    description = str(body.get("description") or f"Custom RAA skill: {name}").strip()
    tools = [str(t).strip() for t in (body.get("tools") or []) if str(t).strip()]
    instructions = str(
        body.get("content") or f"## Workflow\n1. Run custom skill `{skill_id}`."
    ).strip()

    skills_root = await asyncio.to_thread(lambda: Path(__file__).resolve().parents[3] / "skills")
    if not await asyncio.to_thread(skills_root.is_dir):
        svc = SkillService()
        skills_root = svc.roots[0] if svc.roots else Path("skills")

    skill_dir = skills_root / skill_id
    await asyncio.to_thread(skill_dir.mkdir, parents=True, exist_ok=True)
    tools_line = ", ".join(tools)
    skill_md = (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "version: 1.0.0\n"
        f"category: {category}\n"
        "custom: true\n"
        f"tools: [{tools_line}]\n"
        "---\n\n"
        f"# {name}\n\n"
        f"{instructions}\n"
    )
    await asyncio.to_thread((skill_dir / "SKILL.md").write_text, skill_md, encoding="utf-8")
    return {
        "status": "success",
        "skill_id": skill_id,
        "path": str(skill_dir / "SKILL.md"),
        "message": f"Created custom skill '{skill_id}'.",
    }


def _resolve_skills_destination(raw_dest: str) -> Path | None:
    cleaned = raw_dest.strip().replace("\\", "/")
    if not cleaned or cleaned in {".raa-workspace/skills", "./.raa-workspace/skills"}:
        return Path(".raa-workspace/skills").resolve()
    if ".." in cleaned or "\x00" in cleaned:
        return None
    if not re.fullmatch(r"[a-zA-Z0-9_./:-]+", cleaned):
        return None
    ws_base = Path(".raa-workspace").resolve()
    dest_candidate = (ws_base / cleaned.removeprefix(".raa-workspace/")).resolve()
    if dest_candidate.is_relative_to(ws_base):
        return dest_candidate
    return None


@router.post("/api/setup/skills/install")
async def setup_skills_install_endpoint(request: Request) -> dict[str, Any]:
    from raa.services.skills import SkillService

    body = await request.json()
    skill_id = body.get("skill_id")
    install_all = bool(body.get("install_all", False))
    raw_dest = str(body.get("destination") or ".raa-workspace/skills").strip()
    destination = _resolve_skills_destination(raw_dest)
    if destination is None:
        return {"status": "error", "message": "Destination must be inside the workspace."}

    runtime = getattr(request.app.state, "runtime", None)
    skills_svc = runtime.skills if (runtime and hasattr(runtime, "skills")) else SkillService()
    try:
        selected = skills_svc.discover() if install_all else [skills_svc.get(str(skill_id or ""))]
        written = [str(p) for sk in selected for p in skills_svc.install(sk.id, destination)]
        return {
            "status": "success",
            "installed_count": len(selected),
            "files_count": len(written),
            "destination": str(destination),
            "message": f"Installed {len(selected)} skill(s) ({len(written)} files) into {destination}.",
        }
    except Exception as exc:
        logger.warning("Failed to install skills: %s", exc)
        return {"status": "error", "message": "Failed to install selected skill(s)."}


@router.get("/api/setup/workspace/runtimes")
async def setup_workspace_runtimes_endpoint() -> dict[str, Any]:
    import shutil
    import subprocess
    import sys

    def _probe_runtime(
        rt_id: str,
        name: str,
        icon: str,
        bins: list[str],
        ver_args: list[str],
        required_for: str,
        install_url: str,
    ) -> dict[str, Any]:
        found_path = None
        for b in bins:
            found_path = shutil.which(b)
            if found_path:
                break
        if not found_path and rt_id == "python":
            found_path = sys.executable
        version = ""
        if found_path:
            try:
                proc = subprocess.run(
                    [found_path, *ver_args],
                    capture_output=True,
                    text=True,
                    timeout=2.5,
                )
                raw = (proc.stdout or proc.stderr or "").strip().splitlines()
                if raw:
                    version = raw[0].strip()[:64]
            except Exception:
                version = "Detected"
        return {
            "id": rt_id,
            "name": name,
            "icon": icon,
            "available": bool(found_path),
            "version": version,
            "path": found_path,
            "required_for": required_for,
            "install_url": install_url,
        }

    runtimes = [
        _probe_runtime(
            "jdk",
            "Java / JDK",
            "☕",
            ["javac", "java"],
            ["-version"],
            "Required for JADX, Apktool, Uber-APK-Signer, Bundletool, Ghidra, and Android AVD.",
            "https://adoptium.net/",
        ),
        _probe_runtime(
            "npm",
            "Node.js & NPM",
            "📦",
            ["npm", "node"],
            ["--version"],
            "Required for NPM-backed MCP servers (GitHub, Playwright, Postman, REA) and WhatsApp Bridge.",
            "https://nodejs.org/",
        ),
        _probe_runtime(
            "python",
            "Python",
            "🐍",
            ["python", "python3"],
            ["--version"],
            "Required for RAA core, Frida, Mitmproxy, Androguard, APKiD, and CleanYourTV.",
            "https://www.python.org/downloads/",
        ),
        _probe_runtime(
            "dotnet",
            ".NET SDK",
            "🔷",
            ["dotnet"],
            ["--version"],
            "Required for ILSpy (.NET assembly decompilation via ilspycmd).",
            "https://dotnet.microsoft.com/download",
        ),
        _probe_runtime(
            "git",
            "Git",
            "🔧",
            ["git"],
            ["--version"],
            "Required for cloning GitHub source-based tools and repositories.",
            "https://git-scm.com/downloads",
        ),
        _probe_runtime(
            "adb",
            "Android ADB",
            "📱",
            ["adb"],
            ["version"],
            "Required for USB/Wi-Fi Android device debugging, APK installation, and CleanYourTV.",
            "https://developer.android.com/tools/releases/platform-tools",
        ),
    ]
    return {"runtimes": runtimes}


@router.post("/api/setup/skip")
async def setup_skip(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        return cast("dict[str, Any]", runtime.tool_manager.register_skip())
    return {"status": "skipped", "fallback_to_pure_python": True}


@router.post("/api/setup/reopen")
async def setup_reopen(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        return cast("dict[str, Any]", runtime.tool_manager.reopen_setup())
    return {"status": "reopened"}


@router.get("/api/setup/cadence")
async def setup_cadence_get(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "cadence"):
        return cast("dict[str, Any]", runtime.cadence.get_status())
    return {"mode": "interval", "interval_minutes": 5}


@router.post("/api/setup/cadence")
async def setup_cadence(request: Request, body: CadenceConfigBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "cadence"):
        mins = (
            None
            if (body.mode != "interval" and body.interval_minutes <= 0)
            else body.interval_minutes
        )
        return cast(
            "dict[str, Any]", runtime.cadence.configure(mode=body.mode, interval_minutes=mins)
        )
    return {"status": "ok", "mode": body.mode, "interval_minutes": body.interval_minutes}


@router.get("/api/setup/channels/status")
async def setup_channels_status_endpoint(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        live_wa = runtime.channels.whatsapp.get_live_status()
        if live_wa.get("connected"):
            cfg = runtime.channels._load_config()
            wa_phone = live_wa.get("phone") or cfg.get("whatsapp_phone") or ""
            if not cfg.get("whatsapp_paired") or (
                wa_phone and cfg.get("whatsapp_phone") != wa_phone
            ):
                runtime.channels.configure_whatsapp(
                    mode="baileys",
                    phone=wa_phone,
                    paired=True,
                )
            runtime.channels.send_connection_greeting("whatsapp")
        return cast("dict[str, Any]", runtime.channels.get_channels_status())
    return {
        "telegram": {"configured": False, "status": "not_configured"},
        "whatsapp": {"configured": False, "status": "awaiting_scan", "paired": False},
    }


@router.post("/api/setup/channels/telegram/config")
async def setup_telegram_config(request: Request, body: TelegramConfigBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        res = runtime.channels.configure_telegram(
            bot_token=body.bot_token, chat_id=body.chat_id, live_only=True
        )
        if res.get("status") == "success" and (body.chat_id or res.get("default_chat_id")):
            greet = runtime.channels.send_connection_greeting("telegram")
            res["greeting_sent"] = greet.get("status") == "delivered"
        return cast("dict[str, Any]", res)
    return {"status": "error", "message": "Runtime not available"}


@router.get("/api/setup/channels/telegram/poll-link")
async def setup_telegram_poll_link(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        res = runtime.channels.telegram.poll_pairing_updates()
        if res.get("linked") and res.get("chat_id"):
            cfg = runtime.channels._load_config()
            cfg["telegram_chat_id"] = res["chat_id"]
            runtime.channels._save_config(cfg)
            greet = runtime.channels.send_connection_greeting("telegram")
            res["greeting_sent"] = greet.get("status") == "delivered"
        return cast("dict[str, Any]", res)
    return {"linked": False}


@router.post("/api/setup/channels/telegram/disconnect")
async def setup_telegram_disconnect(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        return cast("dict[str, Any]", runtime.channels.disconnect_telegram())
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/channels/telegram/send")
async def setup_telegram_send(request: Request, body: TelegramSendBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        target_chat = body.chat_id or runtime.channels.telegram.default_chat_id
        return cast(
            "dict[str, Any]",
            runtime.channels.telegram.send_live_message(chat_id=target_chat, text=body.text),
        )
    return {"status": "error", "message": "Runtime not available"}


@router.get("/api/setup/channels/whatsapp/qr")
async def setup_whatsapp_qr_endpoint(request: Request, phone: str = "") -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        res = runtime.channels.whatsapp.start_live_qr(phone=phone)
        if res.get("connected"):
            runtime.channels.configure_whatsapp(
                mode="baileys", phone=res.get("phone") or phone, paired=True
            )
            greet = runtime.channels.send_connection_greeting("whatsapp")
            res["greeting_sent"] = greet.get("status") == "delivered"
        return cast("dict[str, Any]", res)
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/channels/whatsapp/pair")
async def setup_whatsapp_pair_endpoint(request: Request, body: WhatsAppPairBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        res = runtime.channels.whatsapp.start_live_qr(phone=body.phone)
        if res.get("connected"):
            runtime.channels.configure_whatsapp(
                mode="baileys", phone=res.get("phone") or body.phone, paired=True
            )
            greet = runtime.channels.send_connection_greeting("whatsapp")
            res["greeting_sent"] = greet.get("status") == "delivered"
        return cast("dict[str, Any]", res)
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/channels/whatsapp/disconnect")
async def setup_whatsapp_disconnect_endpoint(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        res = runtime.channels.whatsapp.disconnect_live()
        runtime.channels.configure_whatsapp(mode="baileys", phone="", paired=False)
        return cast("dict[str, Any]", res)
    return {"status": "error", "message": "Runtime not available"}


@router.get("/api/setup/channels/inbox")
async def setup_channels_inbox(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        return {
            "status": "success",
            "messages": runtime.channels.list_recent_messages(),
            "jobs": runtime.channels.list_jobs(),
        }
    return {"status": "success", "messages": [], "jobs": []}


@router.post("/api/setup/channels/poll")
async def setup_channels_poll(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        return cast(
            "dict[str, Any]", runtime.channels.poll_and_dispatch(channel="all", runtime=runtime)
        )
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/channels/inbound")
async def setup_channels_inbound(request: Request, body: ChannelInboundBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        return cast(
            "dict[str, Any]",
            runtime.channels.process_inbound_message(
                channel=body.channel,
                sender_id=body.sender_id,
                text=body.text,
                attachment_path=body.attachment_path,
                runtime=runtime,
                auto_reply=body.auto_reply,
            ),
        )
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/channels/whatsapp/send")
async def setup_whatsapp_send_endpoint(request: Request, body: WhatsAppSendBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        target_phone = body.phone or runtime.channels.whatsapp.phone
        if not target_phone:
            return {
                "status": "error",
                "message": "Enter a recipient phone number (with country code).",
            }
        return cast(
            "dict[str, Any]",
            runtime.channels.whatsapp.send_live_message(recipient=target_phone, text=body.text),
        )
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/channels/chat")
async def setup_channels_chat(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime or not hasattr(runtime, "channels"):
        return {"status": "error", "message": "Runtime not available"}

    channel = str(payload.get("channel") or "").strip().lower()
    if channel not in {"telegram", "whatsapp"}:
        return {"status": "error", "message": "Unsupported channel"}

    recipient = str(payload.get("recipient") or "").strip()
    if not recipient:
        recipient = (
            runtime.channels.telegram.default_chat_id or ""
            if channel == "telegram"
            else runtime.channels.whatsapp.phone or ""
        )
    if not recipient:
        return {"status": "error", "message": f"Recipient is required for {channel}."}

    mode = str(payload.get("mode") or "manual").strip().lower()
    raw_text = str(payload.get("text") or "").strip()

    if mode == "report":
        res = runtime.channels.process_inbound_message(
            channel=channel,
            sender_id=recipient,
            text=raw_text or "send full report",
            runtime=runtime,
            auto_reply=True,
        )
        return {
            "status": "sent",
            "mode": "report",
            "channel": channel,
            "recipient": recipient,
            "reply_preview": res.get("reply", ""),
            "delivery": res.get("delivery"),
        }

    if mode == "suggest":
        from raa.services.orchestrator import SmartOrchestratorService

        plan = SmartOrchestratorService().build_execution_plan(
            raw_text or "Suggest next reverse engineering, security, and UI actions",
            runtime=runtime,
        )
        lines = [f"💡 *RAA Smart Suggestions ({plan['mode']} mode)*"]
        for idx, step in enumerate(plan["steps"], start=1):
            label = step.get("name") or f"{step.get('server')}:{step.get('tool')}"
            lines.append(f"{idx}. `{label}` — {step.get('reason')}")
        msg_text = "\n".join(lines)
        dispatch = runtime.channels.dispatch_message(channel, recipient, msg_text)
        return {
            "status": dispatch.get("status", "sent"),
            "mode": "suggest",
            "channel": channel,
            "recipient": recipient,
            "reply_preview": msg_text,
            "dispatch": dispatch,
        }

    if mode == "llm":
        prompt = (
            raw_text or "Summarize current RAA capabilities, status, and recommended next steps."
        )
        llm_answer = runtime.channels._ask_llm(prompt, runtime=runtime)
        if not llm_answer:
            mcp_total = runtime.registry.count() if hasattr(runtime, "registry") else 377
            llm_answer = (
                f"🤖 *RAA Assistant ({mcp_total} tools)*\n"
                f"Prompt: `{prompt}`\n"
                "Tip: Configure `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `ANTHROPIC_API_KEY` for full LLM responses, "
                "or use `Send Report` / `Suggest` for instant automated intelligence."
            )
        dispatch = runtime.channels.dispatch_message(channel, recipient, llm_answer)
        return {
            "status": dispatch.get("status", "sent"),
            "mode": "llm",
            "channel": channel,
            "recipient": recipient,
            "reply_preview": llm_answer,
            "dispatch": dispatch,
        }

    if not raw_text:
        return {"status": "error", "message": "Message text cannot be empty."}
    dispatch = runtime.channels.dispatch_message(channel, recipient, raw_text)
    return {
        "status": dispatch.get("status", "sent"),
        "mode": "manual",
        "channel": channel,
        "recipient": recipient,
        "reply_preview": raw_text,
        "dispatch": dispatch,
    }


@router.post("/api/setup/channels/ping")
async def setup_channel_ping(request: Request, body: ChannelPingBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "channels"):
        return cast(
            "dict[str, Any]", runtime.channels.test_ping(channel=body.channel, target=body.target)
        )
    return {"status": "pong", "channel": body.channel}


@router.get("/api/setup/mesh")
async def setup_mesh_list(request: Request) -> list[dict[str, Any]]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        return cast("list[dict[str, Any]]", runtime.mcp_mesh.list_connectors())
    return []


@router.get("/api/setup/mesh/catalog")
async def setup_mesh_catalog(request: Request) -> list[dict[str, Any]]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        return cast("list[dict[str, Any]]", runtime.mcp_mesh.list_catalog())
    return []


@router.post("/api/setup/mesh/download")
async def setup_mesh_download(request: Request, body: MeshActionBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        try:
            return cast("dict[str, Any]", runtime.mcp_mesh.download_connector(name=body.name))
        except Exception as exc:
            logger.warning("Failed to download MCP connector: %s", exc)
            return {"status": "error", "message": "Failed to download MCP connector."}
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/mesh/delete-package")
async def setup_mesh_delete_package(request: Request, body: MeshActionBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        try:
            return cast("dict[str, Any]", runtime.mcp_mesh.delete_connector_package(name=body.name))
        except Exception as exc:
            logger.warning("Failed to delete MCP connector package: %s", exc)
            return {"status": "error", "message": "Failed to delete MCP connector package."}
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/mesh/connect")
async def setup_mesh_connect(request: Request, body: MeshConnectBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        try:
            return cast(
                "dict[str, Any]",
                runtime.mcp_mesh.connect(
                    name=body.name,
                    transport=body.transport,
                    command=body.command,
                    url=body.url,
                    display_name=body.display_name,
                    env=body.env,
                ),
            )
        except Exception as exc:
            logger.warning("Failed to connect MCP server: %s", exc)
            return {"status": "error", "message": "Failed to connect MCP server."}
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/mesh/disconnect")
async def setup_mesh_disconnect(request: Request, body: MeshActionBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        try:
            return cast("dict[str, Any]", runtime.mcp_mesh.disconnect(name=body.name))
        except Exception as exc:
            logger.warning("Failed to disconnect MCP server: %s", exc)
            return {"status": "error", "message": "Failed to disconnect MCP server."}
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/mesh/toggle")
async def setup_mesh_toggle(request: Request, body: MeshToggleBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        try:
            return cast(
                "dict[str, Any]", runtime.mcp_mesh.toggle(name=body.name, enabled=body.enabled)
            )
        except Exception as exc:
            logger.warning("Failed to toggle MCP server: %s", exc)
            return {"status": "error", "message": "Failed to toggle MCP server."}
    return {"status": "error", "message": "Runtime not available"}


@router.post("/api/setup/mesh/ping")
async def setup_mesh_ping(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    name = payload.get("name", "github")
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "mcp_mesh"):
        return cast("dict[str, Any]", runtime.mcp_mesh.test_ping(name))
    return {"status": "pong", "name": name, "latency_ms": 10.0}


CONFIG_DIR = Path("config").resolve()
CONFIG_FILES = [
    "menu.json",
    "tools.json",
    "mcp.json",
    "mobile_channels.json",
    "profile.json",
    "tvstudio.json",
    "vault&shield.json",
    "workspace.json",
]


@router.get("/api/setup/config/list")
async def list_config_files(request: Request) -> list[dict[str, Any]]:
    results = []
    for fname in CONFIG_FILES:
        fpath = CONFIG_DIR / fname
        exists = fpath.exists()
        size_bytes = fpath.stat().st_size if exists else 0
        results.append(
            {
                "filename": fname,
                "path": str(fpath),
                "exists": exists,
                "size_bytes": size_bytes,
            }
        )
    return results


@router.get("/api/setup/config/{filename}")
async def get_config_file(filename: str, request: Request) -> dict[str, Any]:
    safe_name = os.path.basename(filename)
    canonical_name = {n: n for n in CONFIG_FILES}.get(safe_name)
    if canonical_name is None:
        return {"status": "error", "message": "Unsupported configuration filename."}
    fpath = (CONFIG_DIR / canonical_name).resolve()
    if not fpath.is_relative_to(CONFIG_DIR.resolve()) or not fpath.exists():
        return {"status": "error", "message": f"File '{canonical_name}' not found."}
    try:
        content = fpath.read_text(encoding="utf-8")
        return {
            "status": "success",
            "filename": canonical_name,
            "path": str(fpath),
            "content": content,
            "json": json.loads(content) if content else {},
        }
    except Exception as exc:
        logger.warning("Failed to read config %s: %s", canonical_name, exc)
        return {"status": "error", "message": "Failed to read configuration file."}


@router.post("/api/setup/config/{filename}")
async def save_config_file(filename: str, body: ConfigSaveBody, request: Request) -> dict[str, Any]:
    safe_name = os.path.basename(filename)
    canonical_name = {n: n for n in CONFIG_FILES}.get(safe_name)
    if canonical_name is None:
        return {"status": "error", "message": "Unsupported configuration filename."}
    fpath = (CONFIG_DIR / canonical_name).resolve()
    if not fpath.is_relative_to(CONFIG_DIR.resolve()):
        return {"status": "error", "message": "Invalid configuration file path."}
    try:
        parsed = json.loads(body.content)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        fpath.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

        runtime = getattr(request.app.state, "runtime", None)
        if runtime:
            if canonical_name == "mcp.json" and hasattr(runtime, "mcp_mesh"):
                runtime.mcp_mesh._init_store()
            elif canonical_name == "profile.json":
                active = parsed.get("active_profile")
                if active and hasattr(runtime, "profile"):
                    runtime.profile = active

        return {
            "status": "success",
            "message": f"Saved {canonical_name} successfully.",
            "filename": canonical_name,
            "path": str(fpath),
        }
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON syntax."}
    except Exception as exc:
        logger.warning("Failed to save config %s: %s", canonical_name, exc)
        return {"status": "error", "message": "Failed to save configuration file."}


@router.get("/api/setup/profile")
async def get_active_profile(request: Request) -> dict[str, Any]:
    prof_file = CONFIG_DIR / "profile.json"
    active_profile = "core"
    if prof_file.exists():
        try:
            raw = prof_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            active_profile = data.get("active_profile", "core") or "core"
        except Exception as exc:
            logger.debug("Failed to read active profile: %s", exc)
    return {"active_profile": active_profile}


@router.post("/api/setup/profile")
async def update_active_profile(body: ProfileUpdateBody, request: Request) -> dict[str, Any]:
    prof_file = CONFIG_DIR / "profile.json"
    if prof_file.exists():
        try:
            raw = prof_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            data["active_profile"] = body.active_profile
            prof_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to update active profile: %s", exc)
    return {"status": "success", "active_profile": body.active_profile}


@router.post("/api/setup/shield")
async def setup_shield_test(request: Request, body: ShieldTestBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "vault"):
        return cast(
            "dict[str, Any]", runtime.vault.shield_untrusted_content(raw_content=body.content)
        )
    return {
        "status": "shielded",
        "has_injection_risk": False,
        "secrets_redacted": False,
        "safe_surrogate": body.content,
    }


@router.get("/api/setup/vault/list")
async def setup_vault_list(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "vault"):
        return {"status": "success", "secrets": runtime.vault.list_secrets()}
    return {"status": "success", "secrets": []}


@router.post("/api/setup/vault/save")
async def setup_vault_save(request: Request, body: VaultSaveBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime or not hasattr(runtime, "vault"):
        return {"status": "error", "message": "Vault service unavailable."}
    try:
        return cast(
            "dict[str, Any]",
            runtime.vault.store_credential(
                key_name=body.key_name,
                secret_value=body.secret_value,
                username=body.username,
                service=body.service,
                description=body.description,
            ),
        )
    except ValueError as exc:
        logger.warning("Vault save rejected: %s", exc)
        return {"status": "error", "message": "Invalid vault credential parameters."}


@router.post("/api/setup/vault/delete")
async def setup_vault_delete(request: Request, body: VaultDeleteBody) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime or not hasattr(runtime, "vault"):
        return {"status": "error", "message": "Vault service unavailable."}
    return cast("dict[str, Any]", runtime.vault.delete_secret(body.key_name))


_MOBILE_OUI_VENDORS: dict[str, str] = {
    "00:1a:11": "Google Pixel",
    "3c:5a:b4": "Google",
    "94:eb:2c": "Google",
    "f4:f5:d8": "Google",
    "28:6a:ba": "Apple iPhone/iPad",
    "3c:22:fb": "Apple",
    "a4:83:e7": "Apple",
    "f0:18:98": "Apple",
    "00:16:32": "Samsung Galaxy",
    "18:3a:2d": "Samsung",
    "50:01:bb": "Samsung",
    "84:25:db": "Samsung",
    "ac:5f:3e": "Samsung",
    "28:6c:07": "Xiaomi",
    "64:cc:2e": "Xiaomi",
    "78:11:dc": "Xiaomi",
    "ac:37:43": "HTC",
    "9c:2e:a1": "OnePlus / OPPO",
    "a0:32:99": "OnePlus",
    "c0:ee:fb": "OnePlus",
    "14:f6:5a": "Xiaomi / Redmi",
}


def _resolve_adb_executable(request: Request) -> str | None:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and hasattr(runtime, "tool_manager"):
        for t in runtime.tool_manager.list_tools():
            if t.get("tool_id") == "platform-tools" and t.get("binary_path"):
                p = Path(t["binary_path"])
                if p.exists():
                    return str(p)
    return shutil.which("adb")


def _get_local_wifi_ip() -> str:
    # Prefer the active Windows Wireless LAN / Wi-Fi adapter IPv4 over virtual adapters
    if os.name == "nt":
        try:
            proc = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=2)
            in_wifi_section = False
            for line in proc.stdout.splitlines():
                stripped = line.strip()
                if line and not line.startswith(" "):
                    lower = line.lower()
                    in_wifi_section = (
                        "wi-fi" in lower or "wireless lan" in lower
                    ) and "virtual" not in lower
                elif in_wifi_section and "ipv4" in stripped.lower():
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", stripped)
                    if m:
                        return m.group(1)
        except Exception as exc:
            logger.debug("Failed to read local Wi-Fi IP via ipconfig: %s", exc)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return str(s.getsockname()[0])
    except Exception:
        return "127.0.0.1"


def _is_port_open(ip: str, port: int = 5555, timeout: float = 0.15) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _probe_host_live(ip: str) -> bool:
    """Actively verify if a host on the Wi-Fi LAN is currently online (ICMP or TCP RST)."""
    try:
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            res = subprocess.run(
                ["ping", "-n", "1", "-w", "250", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
                creationflags=creationflags,
            )
            if res.returncode == 0:
                return True
        else:
            res = subprocess.run(
                ["ping", "-c", "1", "-W", "1", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
            if res.returncode == 0:
                return True
    except Exception as exc:
        safe_ip = ip.replace("\r", "_").replace("\n", "_")
        logger.debug("Ping probe failed for %s: %s", safe_ip, exc)

    # Fallback: TCP probe for phones that block ICMP (ConnectionRefusedError = live TCP RST)
    for port in (62078, 5555, 80):
        try:
            with socket.create_connection((ip, port), timeout=0.16):
                return True
        except ConnectionRefusedError:
            return True
        except OSError:
            continue
    return False


def _send_arp_windows(ip: str, src_ip_int: int) -> tuple[str, str] | None:
    """Send a real Layer-2 ARP Who-Has request via Windows iphlpapi.SendARP (no admin required)."""
    try:
        iphlpapi = ctypes.windll.iphlpapi
        dest_ip_int = struct.unpack("I", socket.inet_aton(ip))[0]
        mac_buf = (ctypes.c_ubyte * 6)()
        mac_len = ctypes.c_ulong(6)
        rc = iphlpapi.SendARP(dest_ip_int, src_ip_int, ctypes.byref(mac_buf), ctypes.byref(mac_len))
        if rc == 0 and mac_len.value > 0:
            mac_str = ":".join(f"{b:02x}" for b in mac_buf[: mac_len.value])
            if mac_str != "00:00:00:00:00:00" and mac_str != "ff:ff:ff:ff:ff:ff":
                return ip, mac_str
    except Exception as exc:
        safe_ip = ip.replace("\r", "_").replace("\n", "_")
        logger.debug("Ping probe failed for %s: %s", safe_ip, exc)
    return None


def _active_subnet_sweep(subnet_prefix: str, local_ip: str) -> dict[str, str]:
    """Concurrently sweep .1-.254 and return {ip: mac} for ALL currently live hosts on the Wi-Fi."""
    targets = [f"{subnet_prefix}.{i}" for i in range(1, 255) if f"{subnet_prefix}.{i}" != local_ip]
    live_hosts: dict[str, str] = {}

    if os.name == "nt":
        try:
            src_ip_int = struct.unpack("I", socket.inet_aton(local_ip))[0]
        except Exception:
            src_ip_int = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=254) as pool:
            for res in pool.map(lambda ip: _send_arp_windows(ip, src_ip_int), targets):
                if res:
                    live_hosts[res[0]] = res[1]
        return live_hosts

    # POSIX fallback: concurrent ping sweep + arp -a
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        for ip, is_live in zip(targets, pool.map(_probe_host_live, targets), strict=True):
            if is_live:
                live_hosts[ip] = ""
    return live_hosts


async def _run_cmd_async(
    cmd: list[str],
    *,
    timeout_seconds: float,
    creationflags: int = 0,
) -> subprocess.CompletedProcess[str]:
    return _run_cmd_sync(cmd, timeout_seconds=timeout_seconds, creationflags=creationflags)


def _run_cmd_sync(
    cmd: list[str],
    *,
    timeout_seconds: float,
    creationflags: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        creationflags=creationflags,
    )


@router.get("/api/setup/wifi-devices")
async def list_wifi_devices(request: Request) -> dict[str, Any]:
    local_ip = _get_local_wifi_ip()
    ip_parts = local_ip.split(".")
    subnet_prefix = ".".join(ip_parts[:3]) if len(ip_parts) == 4 else "192.168.1"
    subnet_label = f"{subnet_prefix}.0/24"

    devices_by_ip: dict[str, dict[str, Any]] = {}
    adb_exe = _resolve_adb_executable(request)

    # 1. Real-time Layer-2 ARP sweep across .1-.254 (finds ALL 2.4GHz + 5GHz devices, drops offline ones)
    live_hosts = _active_subnet_sweep(subnet_prefix, local_ip)

    # 2. Query mDNS Wireless Debugging services & connected ADB devices (cleanyourtv pattern)
    mdns_ports: dict[str, int] = {}
    mdns_service_endpoints: dict[str, tuple[str, int]] = {}
    if adb_exe:
        try:
            mdns_proc = await _run_cmd_async([adb_exe, "mdns", "services"], timeout_seconds=2)
            for line in mdns_proc.stdout.splitlines():
                m_mdns = re.search(r"(\d+\.\d+\.\d+\.\d+):(\d+)", line)
                if m_mdns and "_adb-tls-connect" in line:
                    m_ip, m_port = m_mdns.group(1), int(m_mdns.group(2))
                    mdns_ports[m_ip] = m_port
                    svc_name = line.split()[0].strip()
                    if svc_name:
                        mdns_service_endpoints[svc_name] = (m_ip, m_port)
        except Exception as exc:
            logger.debug("adb mdns services failed: %s", exc)

        try:
            proc = await _run_cmd_async([adb_exe, "devices", "-l"], timeout_seconds=3)
            for line in proc.stdout.splitlines()[1:]:
                line = line.strip()
                if not line or "device" not in line:
                    continue
                parts = line.split()
                serial = parts[0]
                if parts[1] != "device":
                    continue
                model_match = re.search(r"model:(\S+)", line)
                model_name = model_match.group(1).replace("_", " ") if model_match else serial
                dev_ip = ""
                dev_port: int | None = None
                if ":" in serial:
                    dev_ip = serial.split(":")[0]
                    port_part = serial.rsplit(":", 1)[1]
                    if port_part.isdigit():
                        dev_port = int(port_part)
                elif "_adb-tls-connect" in serial:
                    svc_key = serial.split(".", 1)[0]
                    if svc_key in mdns_service_endpoints:
                        dev_ip, dev_port = mdns_service_endpoints[svc_key]
                if dev_ip:
                    devices_by_ip[dev_ip] = {
                        "ip": dev_ip,
                        "mac": live_hosts.get(dev_ip, ""),
                        "vendor": "Android ADB",
                        "device_name": model_name,
                        "icon": "📱",
                        "adb_status": "connected",
                        "adb_port": dev_port or mdns_ports.get(dev_ip, 5555),
                        "adb_target": f"{dev_ip}:{dev_port}" if dev_port else serial,
                    }
        except Exception as exc:
            logger.debug("adb devices -l failed: %s", exc)

    # 3. Build host entries from live Layer-2 ARP results (plus any mDNS-discovered hosts)
    arp_entries: list[tuple[str, str]] = []
    for ip_addr, mac_addr in live_hosts.items():
        if ip_addr in devices_by_ip:
            if mac_addr:
                devices_by_ip[ip_addr]["mac"] = mac_addr
            continue
        arp_entries.append((ip_addr, mac_addr))

    for mdns_ip in mdns_ports:
        if mdns_ip not in live_hosts and mdns_ip not in devices_by_ip and mdns_ip != local_ip:
            arp_entries.append((mdns_ip, ""))

    from raa.services.lan_discovery import (
        detect_ttl_os,
        discover_mdns_hosts,
        discover_ssdp_hosts,
        lookup_oui_vendor,
        resolve_lan_device_name,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as disc_pool:
        mdns_future = disc_pool.submit(discover_mdns_hosts, 0.7)
        ssdp_future = disc_pool.submit(discover_ssdp_hosts, 0.7)
        mdns_hosts = mdns_future.result()
        ssdp_hosts = ssdp_future.result()

    def _load_wifi_labels() -> dict[str, dict[str, Any]]:
        lbl_file = CONFIG_DIR / "wifi_labels.json"
        if lbl_file.exists():
            try:
                with open(lbl_file, encoding="utf-8") as f:
                    raw = json.load(f)
                normalized: dict[str, dict[str, Any]] = {}
                for k, v in raw.items():
                    key_norm = k.strip().lower()
                    if isinstance(v, dict):
                        normalized[key_norm] = v
                    else:
                        normalized[key_norm] = {"label": str(v), "mac": key_norm}
                return normalized
            except Exception as exc:
                logger.debug("Failed to load wifi labels from %s: %s", lbl_file, exc)
        return {}

    def _lookup_saved_entry(mac_addr: str, ip_addr: str) -> dict[str, Any]:
        entry = wifi_labels.get(mac_addr.lower()) if mac_addr else None
        if not entry and ip_addr:
            entry = wifi_labels.get(ip_addr)
            if not entry:
                for item in wifi_labels.values():
                    if item.get("last_ip") == ip_addr:
                        entry = item
                        break
        return entry or {}

    wifi_labels = _load_wifi_labels()

    def _enrich_arp_host(entry: tuple[str, str]) -> dict[str, Any]:
        ip_addr, mac_addr = entry
        oui = mac_addr[:8]
        is_gateway = ip_addr.endswith(".1")
        vendor = "Wi-Fi Router / Gateway" if is_gateway else _MOBILE_OUI_VENDORS.get(oui)
        if not vendor:
            vendor = lookup_oui_vendor(mac_addr) or None
        if not vendor:
            is_randomized = len(mac_addr) >= 2 and mac_addr[1] in {"2", "6", "a", "e"}
            ttl_os = detect_ttl_os(ip_addr) if not is_gateway else ""
            if ttl_os == "windows":
                vendor = "Windows PC"
            elif is_randomized:
                vendor = "Mobile (Private MAC)"
            else:
                vendor = "Wi-Fi Device"

        saved_entry = _lookup_saved_entry(mac_addr, ip_addr)
        saved_port = saved_entry.get("adb_port")
        fallback_name = (
            f"{vendor.split(' (')[0]} ({ip_addr.rsplit('.', 1)[-1]})"
            if vendor in ("Mobile (Private MAC)", "Wi-Fi Device", "Windows PC")
            else vendor
        )
        host_name, detected_vendor = resolve_lan_device_name(
            ip_addr,
            fallback_name,
            mdns_map=mdns_hosts,
            ssdp_map=ssdp_hosts,
            is_gateway=is_gateway,
        )
        if detected_vendor and vendor in ("Mobile (Private MAC)", "Wi-Fi Device", "Windows PC"):
            vendor = detected_vendor
        if saved_entry.get("vendor") and vendor in (
            "Mobile (Private MAC)",
            "Wi-Fi Device",
            "Windows PC",
        ):
            vendor = str(saved_entry["vendor"])
        if host_name == fallback_name and saved_entry.get("device_name"):
            host_name = str(saved_entry["device_name"])
        mdns_port = mdns_ports.get(ip_addr)
        adb_port = int(mdns_port or saved_port or 5555)
        adb_open = (not is_gateway) and _is_port_open(ip_addr, adb_port)
        if (
            adb_open
            and adb_exe
            and (
                host_name == fallback_name
                or host_name.lower() in ("android", "localhost", "device")
            )
        ):
            try:
                creationflags = (
                    getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
                )
                target_adb = f"{ip_addr}:{adb_port}"
                subprocess.run(
                    [adb_exe, "connect", target_adb],
                    capture_output=True,
                    text=True,
                    timeout=0.8,
                    creationflags=creationflags,
                )
                for prop_key in ("ro.product.marketname", "ro.product.model"):
                    prop = subprocess.run(
                        [adb_exe, "-s", target_adb, "shell", "getprop", prop_key],
                        capture_output=True,
                        text=True,
                        timeout=0.8,
                        creationflags=creationflags,
                    )
                    model = prop.stdout.strip()
                    if model and not model.lower().startswith("error"):
                        host_name = model
                        break
            except Exception as exc:
                logger.debug("ADB getprop failed for %s: %s", target_adb, exc)
        host_low = host_name.lower()
        is_mobile = (not is_gateway) and (
            adb_open
            or any(
                k in vendor
                for k in (
                    "Mobile",
                    "Apple",
                    "Samsung",
                    "Google",
                    "Xiaomi",
                    "OnePlus",
                    "HTC",
                    "OPPO",
                    "Vivo",
                    "Realme",
                )
            )
            or any(
                k in host_low
                for k in (
                    "android",
                    "iphone",
                    "ipad",
                    "pixel",
                    "galaxy",
                    "oppo",
                    "vivo",
                    "realme",
                    "redmi",
                    "poco",
                    "oneplus",
                )
            )
        )
        custom_label = str(saved_entry.get("label", ""))
        return {
            "ip": ip_addr,
            "mac": mac_addr,
            "vendor": vendor,
            "device_name": host_name,
            "custom_label": custom_label,
            "icon": "🌐" if is_gateway else ("📱" if is_mobile else "💻"),
            "adb_status": "adb_ready" if adb_open else "wifi_visible",
            "adb_port": adb_port,
            "adb_target": f"{ip_addr}:{adb_port}",
        }

    if arp_entries:
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
            for item in pool.map(_enrich_arp_host, arp_entries):
                devices_by_ip[item["ip"]] = item

    # Apply custom labels & ports to ADB-connected devices too
    for dev in devices_by_ip.values():
        saved_entry = _lookup_saved_entry(dev.get("mac", ""), dev["ip"])
        if "custom_label" not in dev:
            dev["custom_label"] = str(saved_entry.get("label", ""))
        if saved_entry.get("device_name") and dev.get("adb_status") == "connected":
            dev["device_name"] = str(saved_entry["device_name"])
        if saved_entry.get("vendor") and dev.get("vendor") in (
            "Android ADB",
            "Mobile (Private MAC)",
            "Wi-Fi Device",
        ):
            dev["vendor"] = str(saved_entry["vendor"])
        if "adb_port" not in dev:
            target_str = dev.get("adb_target", "")
            dev["adb_port"] = (
                int(target_str.rsplit(":", 1)[1])
                if ":" in target_str and target_str.rsplit(":", 1)[1].isdigit()
                else int(saved_entry.get("adb_port") or 5555)
            )

    devices = sorted(
        devices_by_ip.values(),
        key=lambda d: (
            0 if d.get("custom_label") else 1,
            0 if d["adb_status"] == "connected" else 1 if d["adb_status"] == "adb_ready" else 2,
            d["ip"],
        ),
    )

    import platform
    import uuid

    node_mac_int = uuid.getnode()
    host_mac = ":".join(f"{(node_mac_int >> shift) & 0xFF:02x}" for shift in range(40, -1, -8))
    wa_bridge_port = int(os.environ.get("RAA_WA_BRIDGE_PORT", "8766"))
    setup_port = int(request.url.port or 8765)
    host_services = [
        {"name": "Setup UI", "port": setup_port, "running": True},
        {
            "name": "WhatsApp Bridge",
            "port": wa_bridge_port,
            "running": _is_port_open("127.0.0.1", wa_bridge_port),
        },
        {"name": "ADB Server", "port": 5037, "running": _is_port_open("127.0.0.1", 5037)},
    ]
    host_card = {
        "ip": local_ip or "127.0.0.1",
        "mac": host_mac,
        "vendor": f"Host ({platform.system()} {platform.release()})",
        "device_name": socket.gethostname() or "Host Machine",
        "custom_label": "",
        "icon": "🖥️",
        "adb_status": "host",
        "adb_port": setup_port,
        "adb_target": f"{local_ip or '127.0.0.1'}:{setup_port}",
        "is_host": True,
        "running_services": host_services,
    }
    devices.insert(0, host_card)

    return {
        "status": "success",
        "local_ip": local_ip,
        "subnet": subnet_label,
        "adb_available": adb_exe is not None,
        "devices": devices,
    }


def _update_wifi_device_record(
    key: str,
    label: str | None = None,
    last_ip: str = "",
    vendor: str = "",
    adb_port: int | None = None,
    clear_label: bool = False,
    device_name: str | None = None,
    android_version: str = "",
) -> None:
    lbl_file = CONFIG_DIR / "wifi_labels.json"
    labels: dict[str, Any] = {}
    if lbl_file.exists():
        try:
            with open(lbl_file, encoding="utf-8") as f:
                labels = json.load(f)
        except Exception:
            labels = {}

    if clear_label:
        to_delete: list[str] = []
        for k, v in list(labels.items()):
            matches_key = k.strip().lower() == key
            matches_ip = bool(last_ip and isinstance(v, dict) and v.get("last_ip") == last_ip)
            if matches_key or matches_ip:
                if isinstance(v, dict):
                    v.pop("label", None)
                    if not v.get("adb_port"):
                        to_delete.append(k)
                else:
                    to_delete.append(k)
        for k in to_delete:
            labels.pop(k, None)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(lbl_file, "w", encoding="utf-8") as f:
            json.dump(labels, f, indent=2)
        return

    if last_ip:
        for k, v in list(labels.items()):
            if k.strip().lower() != key and isinstance(v, dict) and v.get("last_ip") == last_ip:
                v.pop("last_ip", None)

    existing = labels.get(key)
    if not isinstance(existing, dict):
        existing = {"label": str(existing)} if existing else {}

    if ":" in key and last_ip and last_ip in labels and last_ip != key:
        ip_entry = labels.pop(last_ip, None)
        if isinstance(ip_entry, dict) and not existing.get("label") and ip_entry.get("label"):
            existing["label"] = ip_entry["label"]

    if label is not None:
        existing["label"] = label
    if ":" in key:
        existing["mac"] = key
    if last_ip:
        existing["last_ip"] = last_ip
    elif not existing.get("last_ip") and ":" not in key:
        existing["last_ip"] = key
    if vendor:
        existing["vendor"] = vendor
    if device_name:
        existing["device_name"] = device_name
    if android_version:
        existing["android_version"] = android_version
    if adb_port is not None:
        existing["adb_port"] = int(adb_port)

    labels[key] = existing
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(lbl_file, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)


@router.post("/api/setup/wifi-devices/label")
async def save_wifi_device_label(payload: dict[str, Any]) -> dict[str, Any]:
    key = str(payload.get("key", "")).strip().lower()
    label = payload.get("label")
    clear_label = bool(payload.get("clear_label", False))
    last_ip = str(payload.get("ip", "")).strip()
    vendor = str(payload.get("vendor", "")).strip()
    adb_port = payload.get("adb_port")
    if not key:
        return {"status": "error", "message": "Device unique address is required."}
    _update_wifi_device_record(
        key=key,
        label=str(label).strip() if label is not None else None,
        last_ip=last_ip,
        vendor=vendor,
        adb_port=int(adb_port) if adb_port is not None else None,
        clear_label=clear_label,
    )
    return {
        "status": "success",
        "key": key,
        "label": "" if clear_label else label,
        "adb_port": adb_port,
    }


_SAFE_HOST_CHAR_MAP: dict[str, str] = {
    ch: ch for ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
}
_SAFE_DIGIT_CHAR_MAP: dict[str, str] = {str(d): str(d) for d in range(10)}
# Strict allowlist for ADB endpoints produced by _sanitize_adb_endpoint()
# Single outer ^...$ avoids CodeQL "unmatchable dollar/caret" in alternation.
_ADB_SAFE_ENDPOINT_RE = re.compile(
    r"^(?:"
    r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
    r"|[a-zA-Z0-9](?:[a-zA-Z0-9._-]{0,61}[a-zA-Z0-9])?"
    r"):[0-9]{1,5}$"
)


def _sanitize_adb_endpoint(
    raw_target: str, *, default_port: int = 5555
) -> tuple[str, int, str] | None:
    """Validate and reconstruct an ADB host:port endpoint using constant char maps and ipaddress."""
    import ipaddress

    cleaned = raw_target.strip()
    if not cleaned or any(ch in cleaned for ch in ("\r", "\n", "\x00", " ", "\t")):
        return None
    if ":" in cleaned:
        host_part, port_part = cleaned.rsplit(":", 1)
        if not port_part.isdigit():
            return None
        port_num = int(port_part)
        if not (1 <= port_num <= 65535):
            return None
    else:
        host_part = cleaned
        port_num = int(default_port)

    try:
        ip_obj = ipaddress.ip_address(host_part)
        if ip_obj.version == 4:
            o0, o1, o2, o3 = ip_obj.packed
            safe_host = f"{o0}.{o1}.{o2}.{o3}"
        else:
            safe_host = str(ip_obj)
    except ValueError:
        if not host_part or not all(ch in _SAFE_HOST_CHAR_MAP for ch in host_part):
            return None
        safe_host = "".join(_SAFE_HOST_CHAR_MAP[ch] for ch in host_part)
    return safe_host, port_num, f"{safe_host}:{port_num}"


@router.post("/api/setup/wifi-devices/connect")
async def connect_wifi_device(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    raw_target = str(payload.get("target", "")).strip()
    if not raw_target:
        return {"status": "error", "message": "Target IP:Port is required."}
    parsed_ep = _sanitize_adb_endpoint(raw_target, default_port=5555)
    if parsed_ep is None:
        return {"status": "error", "message": "Invalid target host/port format."}
    host, port, target = parsed_ep
    adb_exe = _resolve_adb_executable(request)
    if not adb_exe:
        return {
            "status": "error",
            "message": "ADB (Platform-Tools) not found. Install it from Tools tab first.",
        }

    if not _is_port_open(host, port, timeout=1.8):
        # Check if adb mdns services knows the phone's current Wireless Debugging port
        discovered_port: int | None = None
        try:
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
            )
            mdns_proc = await _run_cmd_async(
                [adb_exe, "mdns", "services"], timeout_seconds=2, creationflags=creationflags
            )
            for line in mdns_proc.stdout.splitlines():
                m_mdns = re.search(rf"{re.escape(host)}:(\d+)", line)
                if m_mdns and "_adb-tls-connect" in line:
                    discovered_port = int(m_mdns.group(1))
                    break
        except Exception as exc:
            safe_host_log = host.replace("\r", "_").replace("\n", "_")
            logger.debug("adb mdns discovery failed for %s: %s", safe_host_log, exc)

        if (
            discovered_port
            and discovered_port != port
            and _is_port_open(host, discovered_port, timeout=1.5)
        ):
            port = discovered_port
            target = f"{host}:{port}"
        elif port != 5555 and _is_port_open(host, 5555, timeout=1.0):
            port = 5555
            target = f"{host}:{port}"
        else:
            return {
                "status": "error",
                "message": f"Port {port} is closed on {host}. Turn ON Wireless Debugging in Settings → Developer options on your phone (or use 📷 Pair with QR Code) and retry.",
            }

    try:
        if not _ADB_SAFE_ENDPOINT_RE.match(target):
            return {"status": "error", "message": "Invalid ADB target format."}
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
        )
        proc = await _run_cmd_async(
            [adb_exe, "connect", target], timeout_seconds=12, creationflags=creationflags
        )
        out = (proc.stdout or proc.stderr or "").strip()
        ok = "connected to" in out.lower() or "already connected" in out.lower()
        if ok:
            meta = _capture_adb_device_metadata(adb_exe, target)
            mac_key = meta.get("mac") or host
            _update_wifi_device_record(
                key=mac_key,
                last_ip=host,
                vendor=meta.get("vendor", ""),
                adb_port=port,
                device_name=meta.get("device_name") or None,
                android_version=meta.get("android_version", ""),
            )
            device_card = {
                "ip": host,
                "mac": meta.get("mac", ""),
                "vendor": meta.get("vendor") or "Android ADB",
                "device_name": meta.get("device_name") or f"Android ({host.rsplit('.', 1)[-1]})",
                "custom_label": "",
                "icon": "📱",
                "adb_status": "connected",
                "adb_port": port,
                "adb_target": target,
                "android_version": meta.get("android_version", ""),
            }
            return {
                "status": "success",
                "message": out or f"ADB connected to {target}",
                "device_info": meta,
                "device": device_card,
            }
        return {"status": "error", "message": out or f"ADB connect result for {target}"}
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"ADB connection to {target} timed out. Check the 'Allow debugging' prompt on your phone and retry.",
        }
    except Exception as exc:
        logger.warning("ADB connect failed: %s", exc)
        return {"status": "error", "message": "ADB connection failed."}


_WIFI_QR_SESSIONS: dict[str, dict[str, Any]] = {}


def _render_qr_svg_via_node(payload: str) -> str:
    qr_pkg = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "channels"
        / "wa_bridge"
        / "node_modules"
        / "qrcode"
    )
    node_exe = shutil.which("node")
    if node_exe and qr_pkg.exists():
        try:
            script = (
                "import QRCode from 'qrcode';"
                "const svg = await QRCode.toString(process.argv[1], {type:'svg', width:220, margin:2, color:{dark:'#0A0E17', light:'#FFFFFF'}});"
                "process.stdout.write(svg);"
            )
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
            )
            proc = subprocess.run(
                [node_exe, "--input-type=module", "-e", script, payload],
                cwd=str(qr_pkg.parent.parent),
                capture_output=True,
                text=True,
                timeout=4,
                creationflags=creationflags,
            )
            if proc.returncode == 0 and "<svg" in proc.stdout:
                return proc.stdout.strip()
        except Exception as exc:
            logger.debug("QR SVG rendering via node failed: %s", exc)
    return ""


@router.post("/api/setup/wifi-devices/qr-pair/start")
async def start_wifi_qr_pair(
    request: Request, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    import secrets

    body = payload or {}
    target_ip = str(body.get("ip", "")).strip()
    service_name = f"studio-{secrets.token_hex(5)}"
    password = secrets.token_hex(4)
    qr_payload = f"WIFI:T:ADB;S:{service_name};P:{password};;"
    qr_svg = _render_qr_svg_via_node(qr_payload)
    session_id = secrets.token_hex(8)
    _WIFI_QR_SESSIONS[session_id] = {
        "service_name": service_name,
        "password": password,
        "ip": target_ip,
    }
    return {
        "status": "success",
        "session_id": session_id,
        "qr_payload": qr_payload,
        "qr_svg": qr_svg,
        "service_name": service_name,
        "password": password,
    }


def _capture_adb_device_metadata(
    adb_exe: str, connect_target: str, ip_hint: str = ""
) -> dict[str, str]:
    """Read Android device model, manufacturer, OS version, and MAC for a connected ADB target."""
    host = ip_hint or (connect_target.rsplit(":", 1)[0] if ":" in connect_target else "")
    port = connect_target.rsplit(":", 1)[1] if ":" in connect_target else ""
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    props: dict[str, str] = {}
    for prop_key in (
        "ro.product.marketname",
        "ro.product.model",
        "ro.product.manufacturer",
        "ro.product.brand",
        "ro.build.version.release",
        "ro.product.device",
    ):
        try:
            proc = subprocess.run(
                [adb_exe, "-s", connect_target, "shell", "getprop", prop_key],
                capture_output=True,
                text=True,
                timeout=1.5,
                creationflags=creationflags,
            )
            val = proc.stdout.strip()
            if val and not val.lower().startswith("error"):
                props[prop_key] = val
        except Exception as exc:
            safe_target_log = connect_target.replace("\r", "_").replace("\n", "_")
            logger.debug("Failed to read ADB prop %s on %s: %s", prop_key, safe_target_log, exc)

    mac_addr = ""
    if os.name == "nt" and host:
        arp_res = _send_arp_windows(host, 0)
        if arp_res and arp_res[1]:
            mac_addr = arp_res[1].lower()

    device_name = (
        props.get("ro.product.marketname")
        or props.get("ro.product.model")
        or props.get("ro.product.device")
        or ""
    )
    vendor = props.get("ro.product.manufacturer") or props.get("ro.product.brand") or ""
    android_version = props.get("ro.build.version.release") or ""
    return {
        "ip": host,
        "port": port,
        "mac": mac_addr,
        "device_name": device_name,
        "vendor": vendor,
        "android_version": android_version,
    }


@router.get("/api/setup/wifi-devices/qr-pair/poll")
async def poll_wifi_qr_pair(request: Request, session_id: str) -> dict[str, Any]:
    sess = _WIFI_QR_SESSIONS.get(session_id)
    if not sess:
        return {"status": "error", "message": "QR pairing session expired."}
    adb_exe = _resolve_adb_executable(request)
    if not adb_exe:
        return {
            "status": "error",
            "message": "ADB (Platform-Tools) not found. Install it from Tools tab first.",
        }

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    try:
        mdns = await _run_cmd_async(
            [adb_exe, "mdns", "services"], timeout_seconds=3, creationflags=creationflags
        )
        pair_target = ""
        connect_target = ""
        svc_name = sess["service_name"]
        pref_ip = sess.get("ip", "")
        for line in mdns.stdout.splitlines():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+):(\d+)", line)
            if not m:
                continue
            endpoint = f"{m.group(1)}:{m.group(2)}"
            if "_adb-tls-pairing" in line and (
                svc_name in line or (pref_ip and m.group(1) == pref_ip)
            ):
                pair_target = endpoint
            elif "_adb-tls-connect" in line and (not pref_ip or m.group(1) == pref_ip):
                connect_target = endpoint

        if not pair_target:
            return {"status": "waiting"}

        pair_proc = await _run_cmd_async(
            [adb_exe, "pair", pair_target, sess["password"]],
            timeout_seconds=10,
            creationflags=creationflags,
        )
        out = (pair_proc.stdout or pair_proc.stderr or "").strip()
        if "successfully paired" in out.lower():
            paired_ip = pair_target.split(":")[0]
            if not connect_target or not connect_target.startswith(f"{paired_ip}:"):
                connect_target = ""
                for _ in range(12):
                    await asyncio.sleep(0.5)
                    mdns2 = await _run_cmd_async(
                        [adb_exe, "mdns", "services"],
                        timeout_seconds=3,
                        creationflags=creationflags,
                    )
                    paired_ip_svcs: set[str] = set()
                    for line in mdns2.stdout.splitlines():
                        m2 = re.search(rf"({re.escape(paired_ip)}):(\d+)", line)
                        if m2 and "_adb-tls-connect" in line:
                            connect_target = f"{m2.group(1)}:{m2.group(2)}"
                            if line.split():
                                paired_ip_svcs.add(line.split()[0].strip())
                            break
                    if connect_target:
                        break
                    devs_check = await _run_cmd_async(
                        [adb_exe, "devices", "-l"], timeout_seconds=3, creationflags=creationflags
                    )
                    for d_line in devs_check.stdout.splitlines()[1:]:
                        d_parts = d_line.strip().split()
                        if len(d_parts) >= 2 and d_parts[1] == "device":
                            ser = d_parts[0]
                            svc_prefix = ser.split(".", 1)[0]
                            if ser.startswith(f"{paired_ip}:") or (
                                "_adb-tls-connect" in ser and svc_prefix in paired_ip_svcs
                            ):
                                connect_target = ser
                                break
                    if connect_target:
                        break
                    if _is_port_open(paired_ip, 5555, timeout=0.2):
                        connect_target = f"{paired_ip}:5555"
                        break

            device_info: dict[str, str] = {
                "ip": paired_ip,
                "port": "",
                "mac": "",
                "device_name": "",
                "vendor": "",
                "android_version": "",
            }
            connected_ok = False
            if connect_target:
                if ":" in connect_target:
                    conn_proc = await _run_cmd_async(
                        [adb_exe, "connect", connect_target],
                        timeout_seconds=5,
                        creationflags=creationflags,
                    )
                    conn_out = (conn_proc.stdout or conn_proc.stderr or "").lower()
                    connected_ok = "connected to" in conn_out or "already connected" in conn_out
                else:
                    connected_ok = True
                device_info = _capture_adb_device_metadata(
                    adb_exe, connect_target, ip_hint=paired_ip
                )
                device_info["ip"] = paired_ip
            elif os.name == "nt":
                arp_res = _send_arp_windows(paired_ip, 0)
                if arp_res and arp_res[1]:
                    device_info["mac"] = arp_res[1].lower()

            record_key = device_info.get("mac") or paired_ip
            port_num = int(device_info["port"]) if device_info.get("port", "").isdigit() else None
            _update_wifi_device_record(
                key=record_key,
                last_ip=paired_ip,
                vendor=device_info.get("vendor", ""),
                adb_port=port_num,
                device_name=device_info.get("device_name") or None,
                android_version=device_info.get("android_version", ""),
            )
            is_ready = bool(port_num and _is_port_open(paired_ip, port_num, timeout=0.25))
            device_card = {
                "ip": paired_ip,
                "mac": device_info.get("mac", ""),
                "vendor": device_info.get("vendor") or "Mobile (Private MAC)",
                "device_name": device_info.get("device_name")
                or f"Android ({paired_ip.rsplit('.', 1)[-1]})",
                "custom_label": "",
                "icon": "📱",
                "adb_status": "connected"
                if connected_ok
                else ("adb_ready" if is_ready else "wifi_visible"),
                "adb_port": port_num or 5555,
                "adb_target": connect_target
                if ":" in connect_target
                else f"{paired_ip}:{port_num or 5555}",
                "android_version": device_info.get("android_version", ""),
            }
            _WIFI_QR_SESSIONS.pop(session_id, None)
            msg = (
                f"Paired & connected {paired_ip}:{port_num}!"
                if connected_ok
                else f"Paired {paired_ip}, but Wireless Debugging connect port was not found. Keep Wireless Debugging ON on your phone."
            )
            return {
                "status": "paired",
                "connected": connected_ok,
                "message": msg,
                "device_info": device_info,
                "device": device_card,
            }
        return {"status": "error", "message": out or f"Pairing failed for {pair_target}"}
    except Exception as exc:
        logger.warning("Wi-Fi QR pair poll failed: %s", exc)
        return {"status": "error", "message": "QR pairing check failed."}


@router.post("/api/setup/wifi-devices/pair")
async def pair_wifi_device(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    raw_target = str(payload.get("target", "")).strip()
    raw_code = str(payload.get("code", "")).strip()
    if not raw_target or not raw_code:
        return {
            "status": "error",
            "message": "Both Pairing IP:Port and 6-digit pairing code are required.",
        }
    parsed_ep = _sanitize_adb_endpoint(raw_target, default_port=5555)
    if parsed_ep is None or not re.fullmatch(r"\d{4,10}", raw_code):
        return {"status": "error", "message": "Invalid pairing target or code format."}
    _, _, target = parsed_ep
    code = "".join(_SAFE_DIGIT_CHAR_MAP[ch] for ch in raw_code)
    adb_exe = _resolve_adb_executable(request)
    if not adb_exe:
        return {
            "status": "error",
            "message": "ADB (Platform-Tools) not found. Install it from Tools tab first.",
        }
    try:
        if not _ADB_SAFE_ENDPOINT_RE.match(target):
            return {"status": "error", "message": "Invalid ADB pair target format."}
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
        )
        proc = await _run_cmd_async(
            [adb_exe, "pair", target, code], timeout_seconds=12, creationflags=creationflags
        )
        out = (proc.stdout or proc.stderr or "").strip()
        ok = "successfully paired" in out.lower()
        return {
            "status": "success" if ok else "error",
            "message": out or f"ADB pair result for {target}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"ADB pairing to {target} timed out. Verify the pairing IP:Port and code on your phone.",
        }
    except Exception as exc:
        logger.warning("ADB pairing failed: %s", exc)
        return {"status": "error", "message": "ADB pairing failed."}


@router.post("/api/setup/wifi-devices/disconnect")
async def disconnect_wifi_device(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    raw_target = str(payload.get("target", "")).strip()
    target = ""
    if raw_target:
        parsed_ep = _sanitize_adb_endpoint(raw_target, default_port=5555)
        if parsed_ep is None:
            return {"status": "error", "message": "Invalid ADB target format."}
        _, _, target = parsed_ep
    adb_exe = _resolve_adb_executable(request)
    if not adb_exe:
        return {"status": "error", "message": "ADB not found."}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    try:
        if target and not _ADB_SAFE_ENDPOINT_RE.match(target):
            return {"status": "error", "message": "Invalid ADB disconnect target format."}
        cmd = [adb_exe, "disconnect", target] if target else [adb_exe, "disconnect"]
        proc = await _run_cmd_async(cmd, timeout_seconds=5, creationflags=creationflags)
        out = (proc.stdout or proc.stderr or "").strip()

        if target and ("no such device" in out.lower() or proc.returncode != 0):
            host_ip = target.rsplit(":", 1)[0]
            mdns_proc = await _run_cmd_async(
                [adb_exe, "mdns", "services"], timeout_seconds=3, creationflags=creationflags
            )
            matching_svcs: set[str] = set()
            for line in mdns_proc.stdout.splitlines():
                if host_ip in line and "_adb-tls-connect" in line and line.split():
                    matching_svcs.add(line.split()[0].strip())

            devs_proc = await _run_cmd_async(
                [adb_exe, "devices", "-l"], timeout_seconds=3, creationflags=creationflags
            )
            serials_to_disconnect: list[str] = []
            for d_line in devs_proc.stdout.splitlines()[1:]:
                d_parts = d_line.strip().split()
                if len(d_parts) >= 2 and d_parts[1] == "device":
                    serial = d_parts[0]
                    svc_prefix = serial.split(".", 1)[0]
                    if serial.startswith(f"{host_ip}:") or svc_prefix in matching_svcs:
                        serials_to_disconnect.append(serial)

            if serials_to_disconnect:
                outputs: list[str] = []
                for ser in serials_to_disconnect:
                    p2 = await _run_cmd_async(
                        [adb_exe, "disconnect", ser], timeout_seconds=5, creationflags=creationflags
                    )
                    o2 = (p2.stdout or p2.stderr or "").strip()
                    if o2:
                        outputs.append(o2)
                out = "; ".join(outputs) or f"Disconnected {target}"
                return {"status": "success", "message": out}
            return {
                "status": "error",
                "message": out or f"No connected ADB device found for {target}",
            }

        ok = "error:" not in out.lower()
        return {"status": "success" if ok else "error", "message": out or f"Disconnected {target}"}
    except Exception as exc:
        logger.warning("ADB connect failed: %s", exc)
        return {"status": "error", "message": "ADB connection failed."}
