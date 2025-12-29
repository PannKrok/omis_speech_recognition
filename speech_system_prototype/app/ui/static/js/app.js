const $ = (id) => document.getElementById(id);

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[c]));
}

function addBubble(role, text) {
  const chat = $("chat");
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.innerHTML = escapeHtml(text);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`${res.status}: ${t}`);
  }
  return await res.json();
}

function openModal(id) { $(id).classList.remove("hidden"); }
function closeModal(id) { $(id).classList.add("hidden"); }

function setTab(tabId) {
  document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-body").forEach(p => p.classList.add("hidden"));
  document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add("active");
  $(tabId).classList.remove("hidden");
}

async function refreshState() {
  const st = await api("/api/state");

  // Settings
  $("voiceAnswers").checked = !!st.settings.voice_answers;
  $("autoConfirm").checked = !!st.settings.auto_confirm;
  $("noiseSuppression").checked = !!st.settings.noise_suppression;
  $("emergencyCommands").checked = !!st.settings.emergency_commands;

  $("voiceTimbre").value = st.settings.voice_timbre || "Женский";
  $("speechSpeed").value = st.settings.speech_speed ?? 1.0;
  $("volume").value = st.settings.volume ?? 80;
  $("tone").value = st.settings.tone || "Стандартный";

  $("speechSpeedHint").innerText = `Текущее значение: ${$("speechSpeed").value}`;
  $("volumeHint").innerText = `Текущее значение: ${$("volume").value}%`;

  // Devices list
  renderDevices(st.devices || []);
}

function renderDevices(devices) {
  const root = $("devicesList");
  root.innerHTML = "";

  devices.forEach(d => {
    const row = document.createElement("div");
    row.className = "device-row";

    const left = document.createElement("div");
    const title = document.createElement("div");
    title.className = "device-title";
    title.textContent = d.name;

    const sub = document.createElement("div");
    sub.className = "device-sub";
    const extra = [];
    extra.push(d.is_on ? "Включено" : "Выключено");
    if (d.value !== null && d.value !== undefined) extra.push(`значение: ${d.value}`);
    extra.push(`тип: ${d.type}`);
    sub.textContent = extra.join(" • ");

    left.appendChild(title);
    left.appendChild(sub);

    const sw = document.createElement("label");
    sw.className = "switch";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = !!d.is_on;
    input.addEventListener("change", async () => {
      await api(`/api/devices/${d.id}/toggle`, {
        method: "POST",
        body: JSON.stringify({ is_on: input.checked }),
      });
      await refreshState();
      addBubble("system", `Устройство «${d.name}» ${input.checked ? "включено" : "выключено"}`);
    });

    const slider = document.createElement("span");
    slider.className = "slider";

    sw.appendChild(input);
    sw.appendChild(slider);

    row.appendChild(left);
    row.appendChild(sw);
    root.appendChild(row);
  });
}

async function sendText() {
  const input = $("textInput");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";

  addBubble("user", text);

  try {
    const resp = await api("/api/chat/send", {
      method: "POST",
      body: JSON.stringify({ text }),
    });

    (resp.messages || []).forEach(m => addBubble("system", m));
    await refreshState();
  } catch (e) {
    addBubble("system", `Ошибка: ${e.message}`);
  }
}

function downsampleBuffer(buffer, sampleRate, outRate) {
  if (outRate === sampleRate) return buffer;
  const ratio = sampleRate / outRate;
  const newLen = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLen);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0, count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = accum / Math.max(1, count);
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

function encodeWavPCM16(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(offset, str) {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  }

  // RIFF header
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");

  // fmt chunk
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);      // PCM
  view.setUint16(20, 1, true);       // audio format
  view.setUint16(22, 1, true);       // channels
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true);       // block align
  view.setUint16(34, 16, true);      // bits per sample

  // data chunk
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  // PCM16 samples
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function initOfflineRecorder() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return null;

  let audioContext = null;
  let stream = null;
  let source = null;
  let processor = null;
  let chunks = [];
  let inputSampleRate = 48000;

  async function start() {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    inputSampleRate = audioContext.sampleRate;

    source = audioContext.createMediaStreamSource(stream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);

    chunks = [];
    processor.onaudioprocess = (e) => {
      const data = e.inputBuffer.getChannelData(0);
      chunks.push(new Float32Array(data));
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
  }

  async function stop() {
    if (!audioContext) return null;

    processor.disconnect();
    source.disconnect();

    stream.getTracks().forEach(t => t.stop());

    const length = chunks.reduce((acc, a) => acc + a.length, 0);
    const merged = new Float32Array(length);
    let offset = 0;
    for (const c of chunks) {
      merged.set(c, offset);
      offset += c.length;
    }

    const outRate = 16000;
    const down = downsampleBuffer(merged, inputSampleRate, outRate);
    const wavBlob = encodeWavPCM16(down, outRate);

    audioContext.close();
    audioContext = null;
    stream = null;
    source = null;
    processor = null;

    return wavBlob;
  }

  return { start, stop };
}

window.addEventListener("DOMContentLoaded", async () => {
  // Modals
  $("settingsBtn").addEventListener("click", () => openModal("settingsModal"));
  $("settingsClose").addEventListener("click", () => closeModal("settingsModal"));
  $("devicesBtn").addEventListener("click", () => openModal("devicesModal"));
  $("devicesClose").addEventListener("click", () => closeModal("devicesModal"));

  // Tabs
  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => setTab(btn.dataset.tab));
  });

  // Send
  $("sendBtn").addEventListener("click", sendText);
  $("textInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendText();
  });
  // Mic (offline): записываем WAV и отправляем на backend (Vosk)
  const recorder = initOfflineRecorder();
  let recording = false;

  if (!recorder) {
    addBubble("system", "Ваш браузер не поддерживает запись звука. Используйте ввод текстом.");
  } else {
    $("micBtn").addEventListener("click", async () => {
      try {
        if (!recording) {
          recording = true;
          $("micBtn").classList.add("active");
          addBubble("system", "Слушаю... Нажмите 🎤 ещё раз, чтобы остановить запись.");
          await recorder.start();
          return;
        }

        recording = false;
        $("micBtn").classList.remove("active");
        const wavBlob = await recorder.stop();
        if (!wavBlob) return;

        addBubble("system", "Распознаю речь оффлайн...");
        const form = new FormData();
        form.append("file", wavBlob, "audio.wav");

        const res = await fetch("/api/asr/transcribe", { method: "POST", body: form });
        const data = await res.json();

        if (!res.ok || !data.ok) {
          const msg = (data && (data.detail || data.message)) ? (data.detail || data.message) : "Ошибка распознавания речи";
          addBubble("system", msg);
          if (String(msg).includes("VOSK model")) {
            addBubble("system", "Проверь VOSK_MODEL_PATH и наличие модели в ./models (см. README).");
          }
          return;
        }

        const text = (data.text || "").trim();
        if (!text) {
          addBubble("system", data.message || "Не удалось распознать. Попробуйте ещё раз.");
          return;
        }

        addBubble("user", text);
        const out = await api("/api/chat/send", { method: "POST", body: JSON.stringify({ text }) });

        // 1) если backend вернул готовые messages — показываем их
        if (Array.isArray(out.messages) && out.messages.length) {
          out.messages.forEach(m => addBubble("system", m));
        } else if (out.reply) {
          // 2) если есть reply — показываем его
          addBubble("system", out.reply);
        } else if (Array.isArray(out.operations) && out.operations.length) {
          // 3) иначе строим текст из последней операции
          const last = out.operations[out.operations.length - 1];
          if (last?.name === "Принятие решений" && last.details) {
            const a = last.details.action || "action";
            const d = last.details.device_id || "device";
            addBubble("system", `Ок: ${a} → ${d}`);
          } else {
            addBubble("system", "Ок.");
          }
        } else {
          addBubble("system", "Ок.");
        }

        await refreshState();
      } catch (e) {
        recording = false;
        $("micBtn").classList.remove("active");
        addBubble("system", "Ошибка микрофона или распознавания речи.");
      }
    });
  }

  // Settings saving

  $("saveMain").addEventListener("click", async () => {
    await api("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        voice_answers: $("voiceAnswers").checked,
        auto_confirm: $("autoConfirm").checked,
        noise_suppression: $("noiseSuppression").checked,
        emergency_commands: $("emergencyCommands").checked,
      }),
    });
    addBubble("system", "Настройки сохранены");
    closeModal("settingsModal");
    await refreshState();
  });

  $("speechSpeed").addEventListener("input", () => {
    $("speechSpeedHint").innerText = `Текущее значение: ${$("speechSpeed").value}`;
  });
  $("volume").addEventListener("input", () => {
    $("volumeHint").innerText = `Текущее значение: ${$("volume").value}%`;
  });

  $("saveStyle").addEventListener("click", async () => {
    await api("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        voice_timbre: $("voiceTimbre").value,
        speech_speed: parseFloat($("speechSpeed").value),
        volume: parseInt($("volume").value, 10),
        tone: $("tone").value,
      }),
    });
    addBubble("system", "Настройки сохранены");
    closeModal("settingsModal");
    await refreshState();
  });

  // Special commands
  $("addServiceWord").addEventListener("click", async () => {
    const word = $("serviceWord").value.trim();
    if (!word) return;
    await api("/api/special/service-word", { method: "POST", body: JSON.stringify({ word }) });
    $("serviceWord").value = "";
    addBubble("system", `Служебное слово «${word}» добавлено`);
  });

  $("saveSequence").addEventListener("click", async () => {
    const name = $("seqName").value.trim();
    const steps = $("seqSteps").value.split("\n").map(s => s.trim()).filter(Boolean);
    if (!name || steps.length === 0) return;
    await api("/api/special/sequence", {
      method: "POST",
      body: JSON.stringify({ name, steps, description: "" }),
    });
    addBubble("system", `Последовательность «${name}» сохранена. Введи в чат ровно: ${name}`);
  });

  // Add device
  $("addDeviceBtn").addEventListener("click", async () => {
    const type = $("newDeviceType").value;
    const name = $("newDeviceName").value.trim() || "Новое устройство";
    await api("/api/devices", {
      method: "POST",
      body: JSON.stringify({ type, name, is_on: false }),
    });
    $("newDeviceName").value = "";
    await refreshState();
  });

  await refreshState();
});
