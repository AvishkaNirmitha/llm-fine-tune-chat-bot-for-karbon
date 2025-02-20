// DOM Elements
const chatMessages = document.getElementById("chat-messages");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const chatContainer = document.querySelector(".chat-container");

// State variables
let isApiCallInProgress = false;
let lastUserMessage = "";
let loaderElement = null;

// Create and append chat icon
const chatIcon = document.createElement("div");
chatIcon.classList.add("chat-icon");
chatIcon.innerHTML = '<i class="fa-solid fa-message"></i>';
document.body.appendChild(chatIcon);

// Input handling functions
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

// Loader functions
function createLoader() {
  // Remove existing loader if any
  const existingLoader = document.querySelector(".loader-container");
  if (existingLoader) {
    existingLoader.remove();
  }

  const loaderContainer = document.createElement("div");
  loaderContainer.className = "loader-container";

  const loader = document.createElement("div");
  loader.className = "loader";

  loaderContainer.appendChild(loader);

  // Insert after chat header
  const chatHeader = document.querySelector(".chat-header");
  chatHeader.insertAdjacentElement("afterend", loaderContainer);

  return loaderContainer;
}

function showLoader() {
  if (!loaderElement) {
    loaderElement = createLoader();
  }
  chatContainer.classList.add("loading");
  loaderElement.classList.add("show");
}

function hideLoader() {
  if (loaderElement) {
    chatContainer.classList.remove("loading");
    loaderElement.classList.remove("show");
  }
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

// Message handling functions
async function handleReaction(messageId, reaction, userMessage, botResponse) {
  try {
    showLoader();
    const API_URL = "http://192.168.1.16:5000/api/reactions";
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        userid: "AV",
        messageId: messageId,
        reaction: reaction === "like" ? 1 : 0,
        userMessage: userMessage,
        botResponse: botResponse,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to send reaction");
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error sending reaction:", error);
  } finally {
    hideLoader();
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

      const API_URL = "http://192.168.1.16:5000/api/messages";
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

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const responseJSON = await response.json();
      console.log('Response from server:', responseJSON);

      typingIndicator.remove();

      // Format the response by replacing newlines with <br> tags
      if (responseJSON?.answer) {
        const formattedAnswer = responseJSON.answer.replace(/\n/g, '<br>');
        addMessage(formattedAnswer, false, false);
      } else {
        throw new Error('Invalid response format from server');
      }

    } catch (error) {
      const typingIndicator = document.querySelector(".typing-indicator");
      if (typingIndicator) {
        typingIndicator.remove();
      }

      console.error("API Error:", error);
      addMessage(
        "Sorry, I encountered an error. Please try again later.",
        false,
        true
      );
    } finally {
      hideLoader();
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
    likeButton.innerHTML = "Like";
    likeButton.onclick = async () => {
      const wasUnliked =
        likeButton.nextElementSibling.classList.contains("active");
      likeButton.nextElementSibling.classList.remove("active");

      const isNowActive = likeButton.classList.toggle("active");

      await handleReaction(
        messageId,
        isNowActive ? "like" : "neutral",
        userMessage,
        message
      );
    };

    const unlikeButton = document.createElement("button");
    unlikeButton.className = "reaction-button unlike";
    unlikeButton.innerHTML = "Unlike";
    unlikeButton.onclick = async () => {
      const wasLiked =
        unlikeButton.previousElementSibling.classList.contains("active");
      unlikeButton.previousElementSibling.classList.remove("active");

      const isNowActive = unlikeButton.classList.toggle("active");

      await handleReaction(
        messageId,
        isNowActive ? "unlike" : "neutral",
        userMessage,
        message
      );
    };

    messageFooter.appendChild(likeButton);
    messageFooter.appendChild(unlikeButton);
    messageDiv.appendChild(messageFooter);
  }

  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Event Listeners
chatIcon.addEventListener("click", () => {
  chatContainer.classList.toggle("open");

  if (chatContainer.classList.contains("open")) {
    chatContainer.style.display = "flex";
    chatIcon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';
  } else {
    chatContainer.style.display = "none";
    chatIcon.innerHTML = '<i class="fa-solid fa-message"></i>';
  }
});

sendButton.addEventListener("click", sendMessage);

messageInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !isApiCallInProgress) {
    sendMessage();
  }
});

// Initialize loader on page load
document.addEventListener("DOMContentLoaded", () => {
  loaderElement = createLoader();
  messageInput.focus();
});
