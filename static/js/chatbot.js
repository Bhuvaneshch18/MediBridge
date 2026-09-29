// VitaDex Health Chatbot - AI Powered
(function() {
    const toggle = document.getElementById('chatbotToggle');
    const window_ = document.getElementById('chatbotWindow');
    const closeBtn = document.getElementById('chatbotClose');
    const input = document.getElementById('chatbotInput');
    const sendBtn = document.getElementById('chatbotSend');
    const messages = document.getElementById('chatbotMessages');

    if (!toggle || !window_) return;

    toggle.addEventListener('click', () => {
        window_.classList.toggle('active');
        if (window_.classList.contains('active')) {
            input.focus();
        }
    });

    closeBtn.addEventListener('click', () => {
        window_.classList.remove('active');
    });

    sendBtn.addEventListener('click', () => sendMessage());
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    let isWaitingForResponse = false;

    async function sendMessage() {
        if (isWaitingForResponse) return;
        
        const text = input.value.trim();
        if (!text) return;
        
        isWaitingForResponse = true;
        input.disabled = true;
        sendBtn.disabled = true;
        
        addMessage(text, 'user');
        input.value = '';
        showTyping();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            removeTyping();

            if (data.error) {
                addMessage("⚠️ " + data.error, 'bot');
            } else {
                // Parse markdown-style basic formatting if needed
                let formattedReply = data.response
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/\n/g, '<br>');
                addMessage(formattedReply, 'bot');
            }
        } catch (error) {
            removeTyping();
            addMessage("⚠️ Connection error. Please make sure the server is running and the API is reachable.", 'bot');
        } finally {
            isWaitingForResponse = false;
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }
    }

    function addMessage(text, type) {
        const div = document.createElement('div');
        div.className = 'chat-message ' + type;
        div.innerHTML = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function showTyping() {
        const div = document.createElement('div');
        div.className = 'typing-indicator';
        div.id = 'typingIndicator';
        div.innerHTML = '<span></span><span></span><span></span>';
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function removeTyping() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    // Make sendChip global for template buttons
    window.sendChip = function(el) {
        const text = el.textContent || el.innerText;
        input.value = text;
        sendMessage();
    };
})();
