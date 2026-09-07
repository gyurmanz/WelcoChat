(function () {
  "use strict";

  var scriptEl = document.currentScript;
  var publicId = scriptEl.getAttribute("data-agent");
  if (!publicId) {
    console.error("Kaptila DeskPilot: missing data-agent attribute on the widget script tag.");
    return;
  }

  var apiBase = scriptEl.src.replace(/\/static\/deskpilot-widget\.js.*$/, "");
  var widgetColor = "#2563eb";

  // Shadow DOM host: isolates the widget from the embedding page's CSS (and
  // vice versa) — see the matching comment in welco-widget.js for why this
  // matters (a host site's global input/button styles can otherwise collapse
  // the widget's own form fields).
  var hostEl = document.createElement("div");
  hostEl.style.cssText = "all:initial;";
  document.body.appendChild(hostEl);
  var root = hostEl.attachShadow({ mode: "open" });

  var bubble = document.createElement("button");
  bubble.setAttribute("aria-label", "Open IT request form");
  bubble.style.cssText =
    "position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;" +
    "border:none;cursor:pointer;z-index:2147483000;box-shadow:0 4px 14px rgba(0,0,0,0.25);" +
    "font-size:24px;color:#fff;background:" + widgetColor + ";";
  bubble.textContent = "🎫";

  var panel = document.createElement("div");
  panel.style.cssText =
    "position:fixed;bottom:88px;right:20px;width:340px;max-width:calc(100vw - 40px);" +
    "max-height:calc(100vh - 120px);background:#fff;border-radius:12px;" +
    "box-shadow:0 8px 30px rgba(0,0,0,0.25);display:none;flex-direction:column;" +
    "overflow:hidden;z-index:2147483000;font-family:system-ui,-apple-system,sans-serif;color:#1e293b;";

  var header = document.createElement("div");
  header.style.cssText = "padding:14px 16px;color:#fff;font-weight:600;font-size:0.95rem;background:" + widgetColor + ";";
  header.textContent = "IT request";

  var body = document.createElement("div");
  body.style.cssText = "padding:14px;overflow-y:auto;";

  var form = document.createElement("form");
  form.style.cssText = "display:flex;flex-direction:column;gap:8px;";

  function makeInput(type, placeholder, required) {
    var el = document.createElement(type === "textarea" ? "textarea" : "input");
    if (type !== "textarea") el.type = type;
    el.placeholder = placeholder;
    if (required) el.required = true;
    el.style.cssText =
      "border:1px solid #cbd5e1;border-radius:6px;padding:8px 10px;font-size:0.85rem;font-family:inherit;";
    if (type === "textarea") el.rows = 4;
    return el;
  }

  var nameInput = makeInput("text", "Your name", false);
  var emailInput = makeInput("email", "Your email", true);
  var textInput = makeInput("textarea", "Describe what you need (e.g. \"I need access to the Marketing shared drive\")", true);

  var submitBtn = document.createElement("button");
  submitBtn.type = "submit";
  submitBtn.textContent = "Submit request";
  submitBtn.style.cssText =
    "border:none;border-radius:6px;color:#fff;padding:9px 14px;font-size:0.85rem;cursor:pointer;background:" + widgetColor + ";";

  var statusMsg = document.createElement("div");
  statusMsg.style.cssText = "font-size:0.8rem;color:#64748b;min-height:1em;";

  form.appendChild(nameInput);
  form.appendChild(emailInput);
  form.appendChild(textInput);
  form.appendChild(submitBtn);
  form.appendChild(statusMsg);
  body.appendChild(form);

  panel.appendChild(header);
  panel.appendChild(body);
  root.appendChild(bubble);
  root.appendChild(panel);

  bubble.addEventListener("click", function () {
    panel.style.display = panel.style.display === "flex" ? "none" : "flex";
  });

  form.addEventListener("submit", function (evt) {
    evt.preventDefault();
    var requestText = textInput.value.trim();
    var email = emailInput.value.trim();
    if (!requestText || !email) return;

    submitBtn.disabled = true;
    statusMsg.textContent = "Submitting…";

    fetch(apiBase + "/widget/deskpilot/" + publicId + "/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requester_name: nameInput.value.trim() || null,
        requester_email: email,
        request_text: requestText,
      }),
    })
      .then(function (r) {
        if (r.status === 402) { throw new Error("suspended"); }
        if (!r.ok) throw new Error("submit failed");
        return r.json();
      })
      .then(function (data) {
        body.innerHTML = "";
        var confirm = document.createElement("div");
        confirm.style.cssText = "font-size:0.85rem;line-height:1.5;";
        confirm.innerHTML =
          "<b>Request received.</b><br>" +
          "Type: " + data.request_type.replace("_", " ") + "<br>" +
          "Summary: " + data.summary + "<br>" +
          (data.routed
            ? "This has been routed to the right approver."
            : "This has been logged and sent to the team for review.");
        body.appendChild(confirm);
      })
      .catch(function (err) {
        submitBtn.disabled = false;
        statusMsg.textContent = (err && err.message === "suspended")
          ? "This service is not currently active."
          : "Something went wrong. Please try again.";
      });
  });
})();
