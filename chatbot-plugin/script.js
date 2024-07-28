document.addEventListener('DOMContentLoaded', function () {
    const chatbotButton = document.getElementById('chatbot-button');
    const chatContainer = document.getElementById('chat-container');
    const sendBtn = document.getElementById('send-btn');
    const closeBtn = document.getElementById('close-btn');
    const userInput = document.getElementById('user-input');
    const output = document.getElementById('output');

    if (!chatbotButton || !chatContainer || !sendBtn || !closeBtn || !userInput || !output) {
        console.error('One or more elements are missing in the DOM.');
        return;
    }

    // Load chat history from local storage
    function loadChatHistory() {
        const chatHistory = localStorage.getItem('chatHistory');
        if (chatHistory) {
            output.innerHTML = chatHistory;
            scrollToBottom()
        }
    }

    // Check if greeting has been sent
    function isGreetingSent() {
        return localStorage.getItem('greetingSent') === 'true';
    }

    // Set greeting sent status
    function setGreetingSent() {
        localStorage.setItem('greetingSent', 'true');
    }

    // Save chat history to local storage
    function saveChatHistory() {
        localStorage.setItem('chatHistory', output.innerHTML);
    }

    chatbotButton.addEventListener('click', function () {
        chatContainer.style.display = 'flex';
        chatbotButton.style.display = 'none';
        console.log('Chatbot button clicked, sending greeting...');
        if (!isGreetingSent()) {
            console.log('Sending greeting...');
            sendGreeting();
            setGreetingSent();
        }
    });

    closeBtn.addEventListener('click', function () {
        chatContainer.style.display = 'none';
        chatbotButton.style.display = 'flex';
    });

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    async function sendGreeting() {
        try {
            const response = await fetch(chatbot_plugin_vars.api_url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: 'GREETING' }),
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            console.log('Chatbot button clicked, sending greeting...');
            const data = await response.json();
            const botMessage = data.response;
            appendMessage('bot', botMessage);
        } catch (error) {
            appendMessage('bot', `Error: Unable to reach the server. ${error.message}`);
        }
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        appendMessage('user', message);
        userInput.value = '';

        const typingIndicator = appendTypingIndicator();
        output.scrollTop = output.scrollHeight;

        try {
            const response = await fetch(chatbot_plugin_vars.api_url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }),
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            const botMessage = data.response;
            removeTypingIndicator(typingIndicator);
            appendMessage('bot', botMessage);
            saveChatHistory();
        } catch (error) {
            removeTypingIndicator(typingIndicator);
            appendMessage('bot', `Error: Unable to reach the server. ${error.message}`);
            saveChatHistory();
        }
    }

    function appendMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);

        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.innerText = message;

        messageElement.appendChild(messageContent);
        output.appendChild(messageElement);
        output.scrollTop = output.scrollHeight;
        scrollToBottom()
        saveChatHistory();
    }

    function appendTypingIndicator() {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'typing');

        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.innerHTML = 'Typing';
        
        const indicator1 = document.createElement('span');
        indicator1.classList.add('typing-indicator');
        
        const indicator2 = document.createElement('span');
        indicator2.classList.add('typing-indicator');
        
        const indicator3 = document.createElement('span');
        indicator3.classList.add('typing-indicator');
        
        messageContent.appendChild(indicator1);
        messageContent.appendChild(indicator2);
        messageContent.appendChild(indicator3);
        
        messageElement.appendChild(messageContent);
        output.appendChild(messageElement);
        output.scrollTop = output.scrollHeight;
        
        return messageElement;
    }

    function removeTypingIndicator(typingIndicator) {
        output.removeChild(typingIndicator);
    }

    function scrollToBottom() {
        output.scrollTop = output.scrollHeight;
    }

    loadChatHistory();
});
