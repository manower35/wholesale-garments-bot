const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const axios = require('axios');
const express = require('express');
const fs = require('fs');
const path = require('path');

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:5000/api/whatsapp/message';
const BRIDGE_PORT = process.env.BRIDGE_PORT || 3001;

let currentQrCode = null;
let currentQrDataUrl = null;
let isConnected = false;

console.log("====================================================");
console.log("  AT SELECTION - WhatsApp Web QR Code Bridge Gateway");
console.log("====================================================");

// Remove stale SingletonLock and lockfile
const sessionLockPath = path.join(__dirname, '.wwebjs_auth', 'session', 'SingletonLock');
if (fs.existsSync(sessionLockPath)) {
    try { fs.unlinkSync(sessionLockPath); console.log('[*] Removed stale SingletonLock.'); } catch (e) {}
}
const sessionLockfilePath = path.join(__dirname, '.wwebjs_auth', 'session', 'lockfile');
if (fs.existsSync(sessionLockfilePath)) {
    try { fs.unlinkSync(sessionLockfilePath); console.log('[*] Removed stale lockfile.'); } catch (e) {}
}

function getExecutablePath() {
    const paths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
        'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'
    ];
    for (const p of paths) { if (fs.existsSync(p)) { console.log(`[*] Using browser: ${p}`); return p; } }
    return undefined;
}

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.3000.1018944884-alpha.html',
    },
    puppeteer: {
        executablePath: getExecutablePath(),
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-accelerated-2d-canvas', '--no-first-run', '--no-zygote', '--disable-gpu',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36']
    }
});

client.on('qr', async (qr) => {
    currentQrCode = qr; isConnected = false;
    try { currentQrDataUrl = await QRCode.toDataURL(qr); } catch (e) { console.error('QR error:', e); }
    console.log('\n[!] FRESH QR CODE! Open http://localhost:3001');
    qrcodeTerminal.generate(qr, { small: true });
});

client.on('authenticated', () => console.log('[+] WhatsApp Authenticated!'));

client.on('ready', () => {
    isConnected = true; currentQrCode = null; currentQrDataUrl = null;
    console.log("====================================================");
    console.log('[+] WhatsApp Bridge Ready & Connected!');
    console.log("====================================================");
});

// Helper: send gallery images one by one with a small delay
async function sendGallery(chatId, gallery) {
    for (let i = 0; i < gallery.length; i++) {
        const item = gallery[i];
        if (item.mediaPath && fs.existsSync(item.mediaPath)) {
            try {
                const media = MessageMedia.fromFilePath(item.mediaPath);
                const caption = item.caption || '';
                await client.sendMessage(chatId, media, { caption });
                console.log(`[📷 Gallery ${i+1}/${gallery.length}] Sent: ${path.basename(item.mediaPath)}`);
                if (i < gallery.length - 1) {
                    await new Promise(r => setTimeout(r, 800));
                }
            } catch (err) {
                console.error(`[!] Failed to send gallery item ${i+1}:`, err.message);
            }
        }
    }
}

client.on('message_create', async (msg) => {
    try {
        if (msg.from.endsWith('@g.us') || msg.from.includes('status')) return;

        // If message is sent by self (fromMe), ONLY process if it's an admin command (#add or #delete)
        if (msg.fromMe) {
            const txt = (msg.body || "").trim().toLowerCase();
            const isAdminCmd = txt.startsWith("#add") || txt.startsWith("/add") || txt.startsWith("add ") ||
                               txt.startsWith("#delete") || txt.startsWith("/delete") || txt.startsWith("delete");
            if (!isAdminCmd) return;
        }

        const contact = await msg.getContact();
        const senderName = contact.pushname || contact.name || contact.number || "Customer";
        const body = (msg.body && msg.body.trim()) ? msg.body.trim() : "";

        // Robust Quoted Message Detection for Swipe-Reply
        let quotedBody = "";
        if (msg.hasQuotedMsg) {
            // Direct synchronous extraction from raw data packet
            if (msg._data) {
                if (msg._data.quotedMsg) {
                    quotedBody = msg._data.quotedMsg.caption || msg._data.quotedMsg.body || "";
                }
                if (!quotedBody && msg._data.quotedBody) {
                    quotedBody = msg._data.quotedBody;
                }
            }
            // Quick fallback with timeout
            if (!quotedBody) {
                try {
                    const quoted = await Promise.race([
                        msg.getQuotedMessage(),
                        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 1500))
                    ]);
                    if (quoted) {
                        quotedBody = quoted.body || quoted.caption || "";
                    }
                } catch (err) {
                    console.log("[!] Quoted message async lookup bypassed:", err.message);
                }
            }
            // Guaranteed fallback tag for swipe replies
            if (!quotedBody) {
                quotedBody = "QUOTED_IMAGE_REPLY";
            }
            console.log(`[💬 Swipe Reply Detected] Quoted Content: "${quotedBody.substring(0, 60)}..."`);
        }

        let mediaData = null;
        let mediaMime = null;
        if (msg.hasMedia) {
            console.log(`[🔍 Media Debug] type: ${msg.type}, fromMe: ${msg.fromMe}, _data keys: ${Object.keys(msg._data || {}).join(', ')}`);
            if (msg._data && msg._data.body) {
                console.log(`[🔍 Media Debug] _data.body length: ${msg._data.body.length}, startsWith: ${msg._data.body.substring(0, 30)}`);
            }
            if (msg.fromMe) {
                await new Promise(r => setTimeout(r, 1200));
            }
            for (let attempt = 1; attempt <= 3; attempt++) {
                try {
                    const media = await msg.downloadMedia();
                    if (media && media.data) {
                        mediaData = media.data;
                        mediaMime = media.mimetype;
                        console.log(`[📸 Media Downloaded] Successfully fetched ${mediaMime} (${media.data.length} bytes)`);
                        break;
                    }
                } catch (mediaErr) {
                    console.error(`[!] Failed to download media payload (attempt ${attempt}/3):`, mediaErr.message || mediaErr);
                    if (attempt < 3) await new Promise(r => setTimeout(r, 1000));
                }
            }
            // Fallback for self-sent images if downloadMedia fails
            if (!mediaData && msg._data && msg._data.body && (msg.type === 'image' || msg.type === 'sticker')) {
                console.log(`[💡 Media Fallback] Using msg._data.body base64 thumbnail for self-sent image!`);
                mediaData = msg._data.body.replace(/^data:image\/\w+;base64,/, '');
                mediaMime = msg.type === 'image' ? 'image/jpeg' : 'image/webp';
            }
        }

        console.log(`\n[📥 Message] From: ${senderName} (${msg.from}) -> "${body}" (hasMedia: ${msg.hasMedia}, hasQuoted: ${msg.hasQuotedMsg})`);

        const response = await axios.post(PYTHON_API_URL, {
            from: msg.from, 
            senderName, 
            body,
            quotedBody,
            hasMedia: msg.hasMedia || false,
            mediaData,
            mediaMime
        }, { headers: { 'Content-Type': 'application/json' }, timeout: 30000 });

        if (response.data) {
            const replyText = response.data.reply || '';
            const mediaPath = response.data.mediaPath;
            const gallery = response.data.gallery;

            // GALLERY MODE: Send header text first, then 10 product photos
            if (gallery && gallery.length > 0) {
                if (replyText) {
                    await msg.reply(replyText);
                    console.log(`[📤 Header] -> "${replyText.replace(/\n/g, ' ').substring(0, 80)}..."`);
                }
                await sendGallery(msg.from, gallery);
                console.log(`[✅ Gallery Complete] Sent ${gallery.length} product photos`);
            }
            // SINGLE IMAGE MODE
            else if (mediaPath && fs.existsSync(mediaPath)) {
                console.log(`[📷 Sending Media] File: ${mediaPath}`);
                const media = MessageMedia.fromFilePath(mediaPath);
                await client.sendMessage(msg.from, media, { caption: replyText });
            }
            // TEXT ONLY MODE
            else if (replyText) {
                console.log(`[📤 Reply] -> "${replyText.replace(/\n/g, ' ').substring(0, 80)}..."`);
                await msg.reply(replyText);
            }
        }
    } catch (error) {
        console.error('[!] Error processing message:', error.message);
        try {
            const logoPath = path.join(__dirname, '..', 'logo.jpg');
            const welcomeText = (
                "🙏 *AT SELECTION*\n" +
                "_Wholesale Readymade Garments_\n" +
                "━━━━━━━━━━━━━━━━━━━━\n" +
                "📍 *Shop:* 1st Floor, Shop 7,8,9, City Plaza Complex, Dewan Dewdi, Hyderabad\n" +
                "📞 *Owner:* Syed Ahmer (+91 9701515477)\n" +
                "━━━━━━━━━━━━━━━━━━━━\n\n" +
                "🛍️ *WHOLESALE GARMENTS CATALOG:*\n" +
                "👉 *Frock & Dresses*\n" +
                "👉 *Plazo & Sharara*\n" +
                "👉 *Western Wear*\n" +
                "👉 *Crop Top & Choli*\n" +
                "👉 *Nightwear & Lounge*\n\n" +
                "📲 *Reply with any Category Name* to view product photos!\n" +
                "👉 *Swipe-Reply* to any photo card for quotation!"
            );
            if (fs.existsSync(logoPath)) {
                const media = MessageMedia.fromFilePath(logoPath);
                await client.sendMessage(msg.from, media, { caption: welcomeText });
            } else {
                await msg.reply(welcomeText);
            }
        } catch (e) {}
    }
});

const app = express();
app.use(express.json());

app.get('/', (req, res) => {
    const head = `
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>AT SELECTION - WhatsApp AI Dashboard</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background: #0b132b; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 16px; }
            .card { background: #1c2541; width: 100%; max-width: 440px; border-radius: 24px; padding: 28px 20px; border: 1px solid #3a506b; box-shadow: 0 20px 40px rgba(0,0,0,0.5); text-align: center; }
            .badge { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 50px; font-weight: 600; font-size: 14px; margin-bottom: 20px; }
            .online { background: rgba(74,222,128,0.15); color: #4ade80; border: 1px solid rgba(74,222,128,0.3); }
            .waiting { background: rgba(251,191,36,0.15); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }
            .loading { background: rgba(56,189,248,0.15); color: #38bdf8; border: 1px solid rgba(56,189,248,0.3); }
            .qr-wrap { background: #fff; padding: 16px; border-radius: 20px; display: inline-block; margin: 20px 0; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
            .qr-img { width: 100%; max-width: 260px; height: auto; display: block; border-radius: 8px; }
            h1 { font-size: 22px; margin-bottom: 8px; font-weight: 700; }
            p { font-size: 14px; color: #94a3b8; line-height: 1.5; }
            .hint { background: #0b132b; padding: 14px; border-radius: 14px; font-size: 13px; color: #fbbf24; margin-top: 20px; border: 1px solid #334155; }
        </style>`;

    if (isConnected) {
        return res.send(`<!DOCTYPE html><html><head>${head}</head><body>
            <div class="card">
                <div class="badge online">🟢 ONLINE & CONNECTED</div>
                <h1>AT SELECTION Bot</h1>
                <p>Your WhatsApp catalog AI is active!</p>
                <div class="hint">📱 Send a message from any phone to browse your wholesale catalog!</div>
            </div></body></html>`);
    }
    if (!currentQrDataUrl) {
        return res.send(`<!DOCTYPE html><html><head>${head}<meta http-equiv="refresh" content="3"></head><body>
            <div class="card"><div class="badge loading">⏳ GENERATING QR...</div><h1>Loading</h1><p>Please wait...</p></div></body></html>`);
    }
    res.send(`<!DOCTYPE html><html><head>${head}<meta http-equiv="refresh" content="10"></head><body>
        <div class="card">
            <div class="badge waiting">📱 PAIRING REQUIRED</div>
            <h1>Scan WhatsApp QR</h1>
            <p>WhatsApp → Settings (⋮) → Linked Devices → Link a Device</p>
            <div class="qr-wrap"><img src="${currentQrDataUrl}" class="qr-img" alt="QR" /></div>
            <div class="hint">✨ Scan immediately. Auto-refreshes every 10s!</div>
        </div></body></html>`);
});

app.listen(BRIDGE_PORT, () => console.log(`[*] Dashboard at http://localhost:${BRIDGE_PORT}`));

async function startClient() {
    try {
        await client.initialize();
    } catch (err) {
        console.log(`[!] WhatsApp initialization error: ${err.message}. Retrying in 3 seconds...`);
        setTimeout(() => startClient(), 3000);
    }
}
startClient();
