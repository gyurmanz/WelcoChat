(function () {
  "use strict";

  var scriptEl = document.currentScript;
  var publicId = scriptEl.getAttribute("data-agent");
  if (!publicId) {
    console.error("WelcoChat: missing data-agent attribute on the widget script tag.");
    return;
  }

  // API base = the origin+path this script was served from, minus the trailing
  // "/static/welco-widget.js" — keeps the widget working from any host
  // without hardcoding a URL inside the file.
  var apiBase = scriptEl.src.replace(/\/static\/welco-widget\.js.*$/, "");

  // Shadow DOM host: fully isolates the widget from the embedding page's CSS
  // (and vice versa). Without this, a host site's global tag selectors (e.g.
  // a WordPress/Elementor theme styling every <input>/<button> on the page)
  // can match and override the widget's own elements directly, regardless of
  // how the widget's inline styles are written — a real case squashed the
  // message input to a sliver. "all:initial" on the host element also stops
  // inherited properties (font, color, line-height) from the page leaking in.
  var hostEl = document.createElement("div");
  hostEl.style.cssText = "all:initial;";
  document.body.appendChild(hostEl);
  var root = hostEl.attachShadow({ mode: "open" });

  var THEMES = {
    light: {
      panelBg: "#fff", bodyText: "#1e293b", borderColor: "#e2e8f0",
      inputBorder: "#cbd5e1", inputBg: "#fff", inputText: "#1e293b",
      assistantBubbleBg: "#f1f5f9", assistantBubbleText: "#1e293b",
      formWrapBg: "#f8fafc", labelText: "#334155", statusMuted: "#64748b",
    },
    dark: {
      panelBg: "#1e293b", bodyText: "#e2e8f0", borderColor: "#334155",
      inputBorder: "#475569", inputBg: "#0f172a", inputText: "#e2e8f0",
      assistantBubbleBg: "#334155", assistantBubbleText: "#e2e8f0",
      formWrapBg: "#0f172a", labelText: "#cbd5e1", statusMuted: "#94a3b8",
    },
  };

  function relativeLuminance(hex) {
    var c = (hex || "#ffffff").replace("#", "");
    if (c.length === 3) c = c.split("").map(function (ch) { return ch + ch; }).join("");
    var r = parseInt(c.substr(0, 2), 16) / 255;
    var g = parseInt(c.substr(2, 2), 16) / 255;
    var b = parseInt(c.substr(4, 2), 16) / 255;
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function buildCustomTheme(bgColor) {
    var bg = bgColor || "#ffffff";
    var isDark = relativeLuminance(bg) < 0.5;
    return isDark
      ? { panelBg: bg, bodyText: "#e2e8f0", borderColor: "#334155", inputBorder: "#475569",
          inputBg: "#0f172a", inputText: "#e2e8f0", assistantBubbleBg: "#334155",
          assistantBubbleText: "#e2e8f0", formWrapBg: "#0f172a", labelText: "#cbd5e1", statusMuted: "#94a3b8" }
      : { panelBg: bg, bodyText: "#1e293b", borderColor: "#e2e8f0", inputBorder: "#cbd5e1",
          inputBg: "#fff", inputText: "#1e293b", assistantBubbleBg: "#f1f5f9",
          assistantBubbleText: "#1e293b", formWrapBg: "#f8fafc", labelText: "#334155", statusMuted: "#64748b" };
  }

  var history = [];
  var widgetName = "Assistant";
  var widgetColor = "#2563eb";
  var greeting = "Hi! How can I help you today?";
  var theme = THEMES.light;
  var contactFormShown = false;

  // Live human handoff: once a conversation is created, subsequent visitor
  // messages go to it instead of the AI /message endpoint, and its replies
  // are picked up by polling.
  var activeConversationId = null;
  var activeConversationToken = null;
  var lastSeenMessageId = 0;
  var pollTimer = null;
  var fallbackTimer = null;
  var FALLBACK_TIMEOUT_MS = 120000;
  var POLL_INTERVAL_MS = 4000;

  // Persist enough state in the visitor's own browser to survive a page
  // reload — no cookie, no new server-side storage. Pre-handoff, we save the
  // same `history` array we already send to /message. Once handed off, the
  // server-stored conversation becomes the single source of truth, so we
  // save only the id and rebuild the thread from GET .../conversations/{id}.
  var STORAGE_KEY = "welcochat_" + publicId;
  var STORAGE_TTL_MS = 24 * 60 * 60 * 1000;

  function loadSavedState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object" || !parsed.savedAt) return null;
      if (Date.now() - parsed.savedAt > STORAGE_TTL_MS) {
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        history: activeConversationId ? [] : history,
        activeConversationId: activeConversationId,
        activeConversationToken: activeConversationToken,
        savedAt: Date.now(),
      }));
    } catch (e) { /* private browsing / quota — degrade silently */ }
  }

  function clearSavedState() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
  }

  var bubble = document.createElement("button");
  bubble.setAttribute("aria-label", "Open chat");
  bubble.style.cssText =
    "position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;" +
    "border:none;cursor:pointer;z-index:2147483000;box-shadow:0 4px 14px rgba(0,0,0,0.25);" +
    "font-size:24px;color:#fff;overflow:hidden;padding:0;";
  bubble.textContent = "💬";

  var panel = document.createElement("div");
  panel.style.cssText =
    "position:fixed;bottom:88px;right:20px;width:340px;max-width:calc(100vw - 40px);" +
    "height:460px;max-height:calc(100vh - 120px);border-radius:12px;" +
    "box-shadow:0 8px 30px rgba(0,0,0,0.25);display:none;flex-direction:column;" +
    "overflow:hidden;z-index:2147483000;font-family:system-ui,-apple-system,sans-serif;box-sizing:border-box;";

  var header = document.createElement("div");
  header.style.cssText = "padding:14px 16px;color:#fff;font-weight:600;font-size:0.95rem;display:flex;align-items:center;gap:8px;";
  var headerLogo = document.createElement("img");
  headerLogo.style.cssText = "width:22px;height:22px;border-radius:50%;object-fit:cover;display:none;flex:none;";
  var headerLabel = document.createElement("span");
  header.appendChild(headerLogo);
  header.appendChild(headerLabel);

  var body = document.createElement("div");
  body.style.cssText = "flex:1;overflow-y:auto;padding:12px;font-size:0.88rem;";

  var attachPreviewWrap = document.createElement("div");
  attachPreviewWrap.style.cssText = "display:none;padding:0 8px;";

  var inputRow = document.createElement("form");
  inputRow.style.cssText = "display:flex;padding:8px;gap:6px;box-sizing:border-box;align-items:center;";
  var attachBtn = document.createElement("button");
  attachBtn.type = "button";
  attachBtn.textContent = "📎";
  attachBtn.setAttribute("aria-label", "Attach an image");
  attachBtn.style.cssText =
    "flex:none;border:none;background:none;cursor:pointer;font-size:1.15rem;padding:4px 2px;display:none;";
  var fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "image/png,image/jpeg,image/webp,image/gif";
  fileInput.style.display = "none";
  var input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Type a message…";
  input.style.cssText =
    "flex:1;min-width:0;border-width:1px;border-style:solid;border-radius:6px;padding:8px 10px;font-size:0.85rem;box-sizing:border-box;";
  var sendBtn = document.createElement("button");
  sendBtn.type = "submit";
  sendBtn.textContent = "Send";
  sendBtn.style.cssText =
    "flex:none;border:none;border-radius:6px;color:#fff;padding:8px 14px;font-size:0.85rem;cursor:pointer;";
  inputRow.appendChild(attachBtn);
  inputRow.appendChild(fileInput);
  inputRow.appendChild(input);
  inputRow.appendChild(sendBtn);

  panel.appendChild(header);
  panel.appendChild(body);
  panel.appendChild(attachPreviewWrap);
  panel.appendChild(inputRow);
  root.appendChild(bubble);
  root.appendChild(panel);

  // Image attachment (Business+ only, gated server-side too): the widget
  // encodes the picked image as base64 and sends it inline with the next
  // /message call — no upload endpoint, no server-side storage, so the image
  // only ever "counts" for that one AI turn (see the chat-image plan notes).
  var MAX_IMAGE_BYTES = 5 * 1024 * 1024;
  var pendingImage = null; // { dataUrl, base64, mediaType }

  function clearPendingImage() {
    pendingImage = null;
    attachPreviewWrap.style.display = "none";
    attachPreviewWrap.innerHTML = "";
    fileInput.value = "";
  }

  function showPendingImagePreview() {
    attachPreviewWrap.innerHTML = "";
    attachPreviewWrap.style.cssText = "display:flex;align-items:center;gap:6px;padding:6px 8px 0;";
    var thumb = document.createElement("img");
    thumb.src = pendingImage.dataUrl;
    thumb.style.cssText = "width:40px;height:40px;object-fit:cover;border-radius:6px;";
    var removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.textContent = "×";
    removeBtn.setAttribute("aria-label", "Remove image");
    removeBtn.style.cssText =
      "border:none;background:none;cursor:pointer;font-size:1rem;color:" + theme.statusMuted + ";";
    removeBtn.addEventListener("click", clearPendingImage);
    attachPreviewWrap.appendChild(thumb);
    attachPreviewWrap.appendChild(removeBtn);
  }

  attachBtn.addEventListener("click", function () {
    fileInput.click();
  });

  fileInput.addEventListener("change", function () {
    var file = fileInput.files && fileInput.files[0];
    if (!file) return;
    if (file.size > MAX_IMAGE_BYTES) {
      addMessage("assistant", "That image is too large (max 5 MB). Please pick a smaller one.");
      fileInput.value = "";
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      var dataUrl = reader.result;
      var base64 = String(dataUrl).split(",")[1] || "";
      pendingImage = { dataUrl: dataUrl, base64: base64, mediaType: file.type };
      showPendingImagePreview();
    };
    reader.readAsDataURL(file);
  });

  function applyTheme() {
    panel.style.background = theme.panelBg;
    body.style.color = theme.bodyText;
    inputRow.style.borderTop = "1px solid " + theme.borderColor;
    input.style.background = theme.inputBg;
    input.style.color = theme.inputText;
    input.style.borderColor = theme.inputBorder;
  }

  function addMessage(role, text, label, imageDataUrl) {
    if (label) {
      var labelEl = document.createElement("div");
      labelEl.textContent = label;
      labelEl.style.cssText =
        "font-size:0.72rem;font-weight:600;color:" + theme.statusMuted + ";margin:2px 0 3px;";
      body.appendChild(labelEl);
    }
    var row = document.createElement("div");
    row.style.cssText =
      "margin-bottom:10px;max-width:85%;padding:8px 10px;border-radius:8px;line-height:1.35;" +
      (role === "user"
        ? "margin-left:auto;background:" + widgetColor + ";color:#fff;"
        : "background:" + theme.assistantBubbleBg + ";color:" + theme.assistantBubbleText + ";");
    if (imageDataUrl) {
      var img = document.createElement("img");
      img.src = imageDataUrl;
      img.style.cssText = "max-width:100%;border-radius:6px;display:block;" + (text ? "margin-bottom:6px;" : "");
      row.appendChild(img);
    }
    if (text) {
      var textNode = document.createElement("div");
      textNode.textContent = text;
      row.appendChild(textNode);
    }
    body.appendChild(row);
    body.scrollTop = body.scrollHeight;
  }

  function applyColor() {
    bubble.style.background = widgetColor;
    header.style.background = widgetColor;
    sendBtn.style.background = widgetColor;
  }

  function transcript() {
    return history.map(function (h) { return h.role + ": " + h.content; }).join("\n");
  }

  function showContactForm() {
    if (contactFormShown) return;
    contactFormShown = true;

    var wrap = document.createElement("div");
    wrap.style.cssText =
      "margin:6px 0 10px;padding:10px;border:1px solid " + theme.borderColor + ";border-radius:8px;background:" + theme.formWrapBg + ";";

    var label = document.createElement("div");
    label.textContent = "Leave your email or WhatsApp number and we'll get back to you shortly.";
    label.style.cssText = "font-size:0.8rem;color:" + theme.labelText + ";margin-bottom:8px;";
    wrap.appendChild(label);

    var form = document.createElement("form");
    form.style.cssText = "display:flex;flex-direction:column;gap:6px;";

    function makeContactInput(type, placeholder) {
      var el = document.createElement("input");
      el.type = type;
      el.placeholder = placeholder;
      el.style.cssText =
        "border:1px solid " + theme.inputBorder + ";border-radius:6px;padding:7px 9px;font-size:0.82rem;" +
        "box-sizing:border-box;background:" + theme.inputBg + ";color:" + theme.inputText + ";";
      return el;
    }

    var emailInput = makeContactInput("email", "Email address");
    var whatsappInput = makeContactInput("tel", "WhatsApp number");

    var submitBtn = document.createElement("button");
    submitBtn.type = "submit";
    submitBtn.textContent = "Send";
    submitBtn.style.cssText =
      "border:none;border-radius:6px;color:#fff;padding:7px 12px;font-size:0.82rem;cursor:pointer;background:" +
      widgetColor + ";align-self:flex-start;";

    var statusMsg = document.createElement("div");
    statusMsg.style.cssText = "font-size:0.76rem;color:#dc2626;min-height:1em;";

    form.appendChild(emailInput);
    form.appendChild(whatsappInput);
    form.appendChild(submitBtn);
    form.appendChild(statusMsg);
    wrap.appendChild(form);
    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;

    form.addEventListener("submit", function (evt) {
      evt.preventDefault();
      var email = emailInput.value.trim();
      var whatsapp = whatsappInput.value.trim();
      if (!email && !whatsapp) {
        statusMsg.textContent = "Please enter an email or WhatsApp number.";
        return;
      }
      submitBtn.disabled = true;
      statusMsg.style.color = theme.statusMuted;
      statusMsg.textContent = "Sending…";

      fetch(apiBase + "/widget/" + publicId + "/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email || null, whatsapp: whatsapp || null, message: transcript(),
          conversation_id: activeConversationId,
        }),
      })
        .then(function (r) {
          if (!r.ok) throw new Error("lead failed");
          wrap.remove();
          addMessage("assistant", "Thanks! We'll be in touch with you shortly.");
        })
        .catch(function () {
          submitBtn.disabled = false;
          statusMsg.style.color = "#dc2626";
          statusMsg.textContent = "Something went wrong. Please try again.";
        });
    });
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null; }
  }

  function handleClosed() {
    stopPolling();
    activeConversationId = null;
    activeConversationToken = null;
    clearSavedState();
    addMessage("assistant", "This conversation has ended. You can keep chatting with the assistant.");
  }

  function startPolling() {
    pollTimer = setInterval(function () {
      fetch(apiBase + "/widget/" + publicId + "/conversations/" + activeConversationId + "/messages?after_id=" + lastSeenMessageId + "&token=" + encodeURIComponent(activeConversationToken || ""))
        .then(function (r) {
          if (!r.ok) throw new Error("poll failed");
          return r.json();
        })
        .then(function (data) {
          data.messages.forEach(function (m) {
            lastSeenMessageId = m.id;
            if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null; }
            addMessage("assistant", m.content, m.sender_name || "Support team");
          });
          if (data.status === "closed") handleClosed();
        })
        .catch(function () { /* transient poll failure — try again on the next tick */ });
    }, POLL_INTERVAL_MS);
  }

  function armFallbackTimer() {
    fallbackTimer = setTimeout(function () {
      fallbackTimer = null;
      showContactForm();
    }, FALLBACK_TIMEOUT_MS);
  }

  function createConversation() {
    fetch(apiBase + "/widget/" + publicId + "/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history: history }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("create conversation failed");
        return r.json();
      })
      .then(function (data) {
        activeConversationId = data.conversation_id;
        activeConversationToken = data.conversation_token;
        lastSeenMessageId = data.last_message_id;
        saveState();
        startPolling();
        armFallbackTimer();
      })
      .catch(function () {
        showContactForm();
      });
  }

  // Reload continuity: a stored activeConversationId means the server-side
  // conversation is the source of truth — rebuild the whole visible thread
  // from it rather than trusting anything kept in memory (there is none,
  // this runs on a fresh page load).
  function resumeConversation(conversationId, conversationToken) {
    activeConversationId = conversationId;
    activeConversationToken = conversationToken;
    attachBtn.style.display = "none";
    fetch(apiBase + "/widget/" + publicId + "/conversations/" + conversationId + "?token=" + encodeURIComponent(conversationToken || ""))
      .then(function (r) {
        if (!r.ok) throw new Error("resume failed");
        return r.json();
      })
      .then(function (data) {
        data.messages.forEach(function (m) {
          lastSeenMessageId = m.id;
          if (m.sender === "visitor") {
            addMessage("user", m.content);
          } else {
            addMessage("assistant", m.content, m.sender === "human" ? (m.sender_name || "Support team") : null);
          }
        });
        if (data.status === "closed") {
          handleClosed();
          return;
        }
        startPolling();
        if (data.status === "waiting") armFallbackTimer();
      })
      .catch(function () {
        // Conversation gone or unreachable — drop the stale reference and
        // fall back to a fresh AI chat rather than getting stuck.
        activeConversationId = null;
        activeConversationToken = null;
        clearSavedState();
        addMessage("assistant", greeting);
      });
  }

  function restoreHistory(savedHistory) {
    history = savedHistory;
    history.forEach(function (h) {
      addMessage(h.role === "user" ? "user" : "assistant", h.content);
    });
  }

  var suspended = false;

  fetch(apiBase + "/widget/" + publicId + "/config")
    .then(function (r) {
      if (r.status === 402) { suspended = true; throw new Error("suspended"); }
      if (!r.ok) throw new Error("config failed");
      return r.json();
    })
    .then(function (cfg) {
      widgetName = cfg.widget_name || widgetName;
      widgetColor = cfg.widget_color || widgetColor;
      greeting = cfg.greeting_message || greeting;
      if (cfg.widget_theme === "custom") {
        theme = buildCustomTheme(cfg.widget_bg_color);
      } else {
        theme = cfg.widget_theme === "dark" ? THEMES.dark : THEMES.light;
      }
      headerLabel.textContent = widgetName;
      if (cfg.widget_logo_url) {
        headerLogo.src = cfg.widget_logo_url;
        headerLogo.style.display = "block";
        bubble.textContent = "";
        var bubbleLogo = document.createElement("img");
        bubbleLogo.src = cfg.widget_logo_url;
        bubbleLogo.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
        bubble.appendChild(bubbleLogo);
      }
      if (cfg.widget_position === "bottom-left") {
        bubble.style.right = "auto";
        bubble.style.left = "20px";
        panel.style.right = "auto";
        panel.style.left = "20px";
      }
      if (cfg.widget_custom_css) {
        var customStyleEl = document.createElement("style");
        customStyleEl.textContent = cfg.widget_custom_css;
        root.appendChild(customStyleEl);
      }
      if (cfg.image_upload_enabled) {
        attachBtn.style.display = "block";
      }
      applyColor();
      applyTheme();

      var saved = loadSavedState();
      if (saved && saved.activeConversationId && saved.activeConversationToken) {
        resumeConversation(saved.activeConversationId, saved.activeConversationToken);
      } else if (saved && saved.history && saved.history.length) {
        restoreHistory(saved.history);
      } else {
        addMessage("assistant", greeting);
      }
    })
    .catch(function () {
      if (suspended) {
        // Subscription isn't active — don't show a broken widget, just don't show one.
        hostEl.remove();
        return;
      }
      headerLabel.textContent = widgetName;
      applyColor();
      applyTheme();
    });

  bubble.addEventListener("click", function () {
    panel.style.display = panel.style.display === "flex" ? "none" : "flex";
  });

  inputRow.addEventListener("submit", function (evt) {
    evt.preventDefault();
    var text = input.value.trim();
    var image = pendingImage;
    if (!text && !image) return;
    input.value = "";
    clearPendingImage();
    addMessage("user", text, null, image ? image.dataUrl : null);

    if (activeConversationId) {
      fetch(apiBase + "/widget/" + publicId + "/conversations/" + activeConversationId + "/messages?token=" + encodeURIComponent(activeConversationToken || ""), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text }),
      }).catch(function () {
        addMessage("assistant", "Sorry, something went wrong. Please try again shortly.");
      });
      return;
    }

    fetch(apiBase + "/widget/" + publicId + "/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        history: history,
        message: text,
        image_data: image ? image.base64 : null,
        image_media_type: image ? image.mediaType : null,
      }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("message failed");
        return r.json();
      })
      .then(function (data) {
        history.push({ role: "user", content: text || "[Image attached]" });
        history.push({ role: "assistant", content: data.reply });
        addMessage("assistant", data.reply);
        if (data.handoff) {
          attachBtn.style.display = "none";
          createConversation();
        } else {
          saveState();
        }
      })
      .catch(function () {
        addMessage("assistant", "Sorry, something went wrong. Please try again shortly.");
      });
  });
})();
