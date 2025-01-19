const axios = require("axios");

// API endpoint and payload
const API_URL = "http://127.0.0.1:5000/api/messages";
const PAYLOAD = {
  message: "hello how are you?",
  type: "text",
  userid: "12345",
};

// Function to send a POST request
async function sendRequest(index) {
  try {
    const response = await axios.post(API_URL, PAYLOAD);
    console.log(`Request ${index}:`, response?.data?.answer);
    return response;
  } catch (error) {
    if (error.response) {
      console.error(`Request ${index} failed:`, error.response.data);
    } else {
      console.error(`Request ${index} failed:`, error.message);
    }
  }
}

// Send 26 requests to test the rate limit
(async () => {
  for (let i = 1; i <= 10; i++) {
    // const result = await sendRequest(i);
    // console.log(i, "--->", result?.data?.answer);
    // console.log(i, "--->", result?.data);

    sendRequest(i);
  }
})();
