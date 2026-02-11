import './TypingIndicator.css';

export default function TypingIndicator() {
  return (
    <div className="typing-indicator-wrapper">
      <div className="avatar assistant-avatar">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
        </svg>
      </div>
      <div className="typing-bubble">
        <div className="typing-dots">
          <span></span><span></span><span></span>
        </div>
        <span className="typing-text">Analyzing your data...</span>
      </div>
    </div>
  );
}
