let chatHistory = [];

function appendToThread(role, text) {
  const thread = document.getElementById("chat-thread");
  const placeholder = thread.querySelector(".chat-placeholder");
  if (placeholder) placeholder.remove();

  const msg = document.createElement("div");
  msg.className = `chat-msg chat-msg-${role}`;

  const label = document.createElement("div");
  label.className = "chat-role-label";
  label.textContent = role === "user" ? "Você" : "Agente";

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";
  bubble.textContent = text;

  if (role === "user") {
    msg.appendChild(bubble);
    msg.appendChild(label);
  } else {
    msg.appendChild(label);
    msg.appendChild(bubble);
  }

  thread.appendChild(msg);
  thread.scrollTop = thread.scrollHeight;
  return bubble;
}

async function sendQuestion() {
  const questionEl = document.getElementById("chat-question");
  const sendBtn = document.getElementById("chat-send-button");
  const statusEl = document.getElementById("chat-status");

  const message = questionEl.value.trim();
  if (!message) return;

  sendBtn.disabled = true;
  statusEl.textContent = "Consultando o agente...";
  questionEl.value = "";

  appendToThread("user", message);

  const startedAt = Date.now();

  try {
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: chatHistory }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const assistantAnswer = await readStreamedChat(response, statusEl, startedAt);
    if (assistantAnswer) {
      chatHistory.push({ role: "user", content: message });
      chatHistory.push({ role: "assistant", content: assistantAnswer });
      if (chatHistory.length > 16) chatHistory = chatHistory.slice(-16);
    }
  } catch (_err) {
    await fallbackChat(message, statusEl, startedAt);
  }

  sendBtn.disabled = false;
}

async function readStreamedChat(response, statusBox, startedAt) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let firstToken = true;
  let fullText = "";

  const bubble = appendToThread("assistant", "");
  const thread = document.getElementById("chat-thread");

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const lines = decoder.decode(value).split("\n").filter(l => l.trim());
    for (const line of lines) {
      try {
        const chunk = JSON.parse(line);
        if (chunk.token) {
          if (firstToken) {
            const ttft = ((Date.now() - startedAt) / 1000).toFixed(1);
            statusBox.textContent = `Primeira palavra em ${ttft}s...`;
            firstToken = false;
          }
          fullText += chunk.token;
          bubble.textContent = fullText;
          thread.scrollTop = thread.scrollHeight;
        }
        if (chunk.done) {
          const total = ((Date.now() - startedAt) / 1000).toFixed(1);
          statusBox.textContent = `Resposta completa em ${total}s.`;
        }
        if (chunk.error) {
          bubble.textContent = chunk.error;
          statusBox.textContent = "Erro na resposta.";
        }
      } catch (_e) {}
    }
  }

  return fullText;
}

async function fallbackChat(message, statusBox, startedAt) {
  try {
    statusBox.textContent = "Usando modo direto...";
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: chatHistory }),
    });
    const data = await response.json();
    const answer = data.answer || data.error || "Erro desconhecido.";
    appendToThread("assistant", answer);
    const total = ((Date.now() - startedAt) / 1000).toFixed(1);
    statusBox.textContent = `Resposta em ${total}s.`;
    if (data.history) chatHistory = data.history;
  } catch (_e) {
    appendToThread("assistant", "Erro ao contatar o servidor.");
    statusBox.textContent = "Falha na requisição.";
  }
}

function clearHistory() {
  chatHistory = [];
  document.getElementById("chat-thread").innerHTML =
    '<div class="chat-placeholder">Histórico limpo. Faça uma nova pergunta.</div>';
  document.getElementById("chat-status").textContent = "Pronto para consultar o modelo local.";
}

function fillAndSend(text) {
  document.getElementById("chat-question").value = text;
  sendQuestion();
}

document.addEventListener("DOMContentLoaded", () => {
  const textarea = document.getElementById("chat-question");
  if (textarea) {
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendQuestion();
      }
    });
  }
});
