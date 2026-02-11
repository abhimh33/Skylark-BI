import { useState, useRef, useCallback } from 'react';
import { askQuestion } from '../services/api';

const WELCOME_MSG = {
  id: '1',
  role: 'assistant',
  content:
    "Hello! I'm your **SkyLark BI** assistant. Ask me anything about your deals pipeline, work orders, revenue, or collection metrics.\n\nTry asking:\n- *\"Give me a leadership update\"*\n- *\"What's our total pipeline value?\"*\n- *\"How's collection efficiency looking?\"*\n- *\"Break down pipeline by sector\"*",
  timestamp: new Date(),
  suggestedQuestions: [
    'Give me a leadership update',
    "What's our total pipeline value?",
    'Show collection efficiency',
    'Pipeline by sector breakdown',
  ],
};

export function useChat() {
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(
    async (question) => {
      if (!question.trim() || isLoading) return;

      const userMsg = {
        id: Date.now().toString(),
        role: 'user',
        content: question.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const data = await askQuestion(question.trim());

        const assistantMsg = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.insights,
          metrics: data.key_metrics,
          warnings: data.data_quality_warnings,
          confidence: data.confidence,
          processingTime: data.processing_time_ms,
          requiresClarification: data.requires_clarification,
          suggestedQuestions: data.suggested_questions || [],
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Sorry, something went wrong: ${err.message}. Please try again.`,
          isError: true,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading]
  );

  const clearChat = useCallback(() => {
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: 'Chat cleared. How can I help you with your business data?',
        timestamp: new Date(),
        suggestedQuestions: WELCOME_MSG.suggestedQuestions,
      },
    ]);
  }, []);

  return { messages, isLoading, sendMessage, clearChat };
}
