import ReactMarkdown from 'react-markdown';
import { AlertTriangle, Info, AlertCircle, Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import './ChatMessage.css';

function MetricCard({ metric }) {
  const getTrendIcon = (trend) => {
    if (trend === 'up') return <TrendingUp size={14} className="trend-up" />;
    if (trend === 'down') return <TrendingDown size={14} className="trend-down" />;
    return <Minus size={14} className="trend-stable" />;
  };

  return (
    <div className="metric-card">
      <div className="metric-header">
        <span className="metric-name">{metric.description}</span>
        {metric.trend && getTrendIcon(metric.trend)}
      </div>
      <div className="metric-value">{metric.formatted_value}</div>
    </div>
  );
}

function WarningBadge({ warning }) {
  const severity = warning.severity || 'warning';
  const Icon = severity === 'error' ? AlertCircle : severity === 'info' ? Info : AlertTriangle;
  return (
    <div className={`warning-badge severity-${severity}`}>
      <Icon size={12} />
      <span>{warning.issue}</span>
    </div>
  );
}

export default function ChatMessage({ message, onSuggestionClick }) {
  const isUser = message.role === 'user';

  return (
    <div className={`chat-message ${isUser ? 'user' : 'assistant'} ${message.isError ? 'error' : ''}`}>
      {!isUser && (
        <div className="avatar assistant-avatar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
          </svg>
        </div>
      )}

      <div className="message-content">
        <div className="message-bubble">
          <ReactMarkdown
            components={{
              h2: ({ children }) => <h2 className="md-h2">{children}</h2>,
              h3: ({ children }) => <h3 className="md-h3">{children}</h3>,
              p: ({ children }) => <p className="md-p">{children}</p>,
              ul: ({ children }) => <ul className="md-ul">{children}</ul>,
              ol: ({ children }) => <ol className="md-ol">{children}</ol>,
              li: ({ children }) => <li className="md-li">{children}</li>,
              strong: ({ children }) => <strong className="md-strong">{children}</strong>,
              em: ({ children }) => <em className="md-em">{children}</em>,
              code: ({ children }) => <code className="md-code">{children}</code>,
              hr: () => <hr className="md-hr" />,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {message.metrics && message.metrics.length > 0 && (
          <div className="metrics-grid">
            {message.metrics.map((m, i) => (
              <MetricCard key={i} metric={m} />
            ))}
          </div>
        )}

        {message.warnings && message.warnings.length > 0 && (
          <div className="warnings-list">
            <span className="warnings-label">Data Notes</span>
            {message.warnings.map((w, i) => (
              <WarningBadge key={i} warning={w} />
            ))}
          </div>
        )}

        {message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
          <div className="suggested-questions">
            {message.suggestedQuestions.map((q, i) => (
              <button
                key={i}
                className="suggestion-chip-inline"
                onClick={() => onSuggestionClick?.(q)}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {message.processingTime && (
          <div className="message-meta">
            <Clock size={11} />
            <span>{(message.processingTime / 1000).toFixed(1)}s</span>
          </div>
        )}
      </div>

      {isUser && (
        <div className="avatar user-avatar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      )}
    </div>
  );
}
