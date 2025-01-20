const chatMessages = document.getElementById("chat-messages");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const chatContainer = document.querySelector(".chat-container");
let isApiCallInProgress = false;
let lastUserMessage = "";

// Create and append chat icon dynamically to the body or container
const chatIcon = document.createElement("div");
chatIcon.classList.add("chat-icon");
chatIcon.innerHTML = '<i class="fa-solid fa-message"></i>';
document.body.appendChild(chatIcon);

function disableInput() {
  messageInput.disabled = true;
  sendButton.disabled = true;
}

function enableInput() {
  messageInput.disabled = false;
  sendButton.disabled = false;
  messageInput.focus();
}

function getTimestamp() {
  return new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function showTypingIndicator() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "typing-indicator";
  typingDiv.innerHTML = `
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        `;
  chatMessages.appendChild(typingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return typingDiv;
}

async function handleReaction(messageId, reaction, userMessage, botResponse) {
  try {
    const API_URL = "http://192.168.1.24:5000/api/reactions";
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        userid: "AV",
        messageId: messageId,
        reaction: reaction == "like" ? 1 : 0,
        userMessage: userMessage,
        botResponse: botResponse,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to send reaction");
    }

    return await response.json();
  } catch (error) {
    console.error("Error sending reaction:", error);
  }
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (message && !isApiCallInProgress) {
    try {
      isApiCallInProgress = true;
      disableInput();
      lastUserMessage = message;

      addMessage(message, true);
      messageInput.value = "";

      const typingIndicator = showTypingIndicator();

      const API_URL = "http://192.168.1.24:5000/api/messages";
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          userid: "AV",
          type: 1,
          message: message,
        }),
      });

      const responseJSON = await response.json();
      typingIndicator.remove();
      addMessage(responseJSON?.answer, false, false);
    } catch (error) {
      const typingIndicator = document.querySelector(".typing-indicator");
      if (typingIndicator) {
        typingIndicator.remove();
      }
      addMessage(
        "Sorry, I encountered an error. Please try again later.",
        false,
        true
      );
      console.error("API Error:", error);
    } finally {
      isApiCallInProgress = false;
      enableInput();
    }
  }
}

function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return text.replace(urlRegex, function (url) {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${"view on doc"}</a>`;
  });
}

function addMessage(message, isUser, isError = false) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${isUser ? "user-message" : "bot-message"} ${
    isError ? "error-message" : ""
  }`;

  const messageContent = document.createElement("div");
  messageContent.className = "message-content";
  messageContent.innerHTML = linkify(message);

  const timestamp = document.createElement("div");
  timestamp.className = "message-timestamp";
  timestamp.textContent = getTimestamp();

  messageDiv.appendChild(messageContent);
  messageDiv.appendChild(timestamp);

  if (!isUser && !isError) {
    const messageFooter = document.createElement("div");
    messageFooter.className = "message-footer";

    const messageId = Date.now().toString();
    const userMessage = lastUserMessage;

    const likeButton = document.createElement("button");
    likeButton.className = "reaction-button like";
    likeButton.innerHTML = "👍 Like";
    likeButton.onclick = async () => {
      const wasUnliked =
        likeButton.nextElementSibling.classList.contains("active");
      likeButton.nextElementSibling.classList.remove("active");
      likeButton.classList.toggle("active");

      if (likeButton.classList.contains("active")) {
        await handleReaction(messageId, "like", userMessage, message);
      } else {
        await handleReaction(messageId, "neutral", userMessage, message);
      }
    };

    const unlikeButton = document.createElement("button");
    unlikeButton.className = "reaction-button unlike";
    unlikeButton.innerHTML = "👎 Unlike";
    unlikeButton.onclick = async () => {
      const wasLiked =
        unlikeButton.previousElementSibling.classList.contains("active");
      unlikeButton.previousElementSibling.classList.remove("active");
      unlikeButton.classList.toggle("active");

      if (unlikeButton.classList.contains("active")) {
        await handleReaction(messageId, "unlike", userMessage, message);
      } else {
        await handleReaction(messageId, "neutral", userMessage, message);
      }
    };

    messageFooter.appendChild(likeButton);
    messageFooter.appendChild(unlikeButton);
    messageDiv.appendChild(messageFooter);
  }

  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Chat icon click event
chatIcon.addEventListener("click", () => {
  // Toggle 'open' class for smooth animation
  chatContainer.classList.toggle("open");

  // Toggle icon to close or open
  if (chatContainer.classList.contains("open")) {
    chatContainer.style.display = "flex";
    chatIcon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i></i>'; // Close icon
  } else {
    chatContainer.style.display = "none";
    chatIcon.innerHTML = '<i class="fa-solid fa-message"></i>'; // Open icon
  }
});

// Event listeners
sendButton.addEventListener("click", sendMessage);
messageInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !isApiCallInProgress) {
    sendMessage();
  }
});

// Focus input on page load
messageInput.focus();
