import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import './ChatInput.css';

const DEFAULT_SUGGESTIONS = [
  'Give me a leadership update',
  "What's our total pipeline value?",
  'Show collection efficiency',
  'Pipeline by sector breakdown',
];

export default function ChatInput({ onSend, disabled, dynamicSuggestions = [] }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const suggestions = dynamicSuggestions.length > 0 ? dynamicSuggestions : DEFAULT_SUGGESTIONS;

  return (
    <div className="chat-input-container">
      {input === '' && (
        <div className="suggestions">
          {suggestions.map((s, i) => (
            <button
              key={i}
              className="suggestion-chip"
              onClick={() => { onSend(s); }}
              disabled={disabled}
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your business data..."
          disabled={disabled}
          rows={1}
        />
        <button
          type="submit"
          className="send-button"
          disabled={!input.trim() || disabled}
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
