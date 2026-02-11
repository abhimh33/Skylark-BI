import { useRef, useEffect } from 'react';
import { Trash2 } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import TypingIndicator from './TypingIndicator';
import './ChatWindow.css';

export default function ChatWindow() {
  const { messages, isLoading, sendMessage, clearChat } = useChat();
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Get suggestions from the last assistant message
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === 'assistant');
  const dynamicSuggestions = lastAssistantMsg?.suggestedQuestions || [];

  return (
    <div className="chat-window">
      <header className="chat-header">
        <div className="header-left">
          <div className="logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div>
            <h1 className="header-title">SkyLark BI</h1>
            <span className="header-subtitle">Business Intelligence Agent</span>
          </div>
        </div>
        <button className="clear-btn" onClick={clearChat} title="Clear chat">
          <Trash2 size={16} />
        </button>
      </header>

      <div className="messages-area">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} onSuggestionClick={sendMessage} />
        ))}
        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSend={sendMessage} disabled={isLoading} dynamicSuggestions={dynamicSuggestions} />
    </div>
  );
}
