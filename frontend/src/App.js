
import React, { useState, useEffect } from "react";
import axios from "axios";

function App() {

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalQueries: 0,
    avgResponseTime: 0,
    totalTime: 0
  });
  const [responseTime, setResponseTime] = useState(0);
  const [displayedAnswer, setDisplayedAnswer] = useState("");
  const [liveTime, setLiveTime] = useState(new Date());
  const [displayedStats, setDisplayedStats] = useState({
    totalQueries: 0,
    avgResponseTime: 0,
    responseTime: 0
  });

  useEffect(() => {
    const intervalId = setInterval(() => {
      setLiveTime(new Date());
    }, 1000);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (!answer) {
      setDisplayedAnswer("");
      return;
    }

    let index = 0;
    setDisplayedAnswer("");

    const intervalId = setInterval(() => {
      index += 2;
      setDisplayedAnswer(answer.slice(0, index));
      if (index >= answer.length) {
        clearInterval(intervalId);
      }
    }, 12);

    return () => clearInterval(intervalId);
  }, [answer]);

  useEffect(() => {
    const durationMs = 350;
    const start = performance.now();
    const from = {
      totalQueries: displayedStats.totalQueries,
      avgResponseTime: displayedStats.avgResponseTime,
      responseTime: displayedStats.responseTime
    };
    const to = {
      totalQueries: stats.totalQueries,
      avgResponseTime: stats.avgResponseTime,
      responseTime: responseTime
    };

    const animate = (now) => {
      const progress = Math.min((now - start) / durationMs, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setDisplayedStats({
        totalQueries: Math.round(from.totalQueries + (to.totalQueries - from.totalQueries) * ease),
        avgResponseTime: Math.round(from.avgResponseTime + (to.avgResponseTime - from.avgResponseTime) * ease),
        responseTime: Math.round(from.responseTime + (to.responseTime - from.responseTime) * ease)
      });

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [stats.totalQueries, stats.avgResponseTime, responseTime]);

  const askQuestion = async () => {

    if (!question) return;

    setLoading(true);
    const startTime = Date.now();

    try {

      const response = await axios.post(
        "http://127.0.0.1:5000/ask",
        { question: question }
      );

      const endTime = Date.now();
      const time = endTime - startTime;
      setResponseTime(time);

      setAnswer(response.data.answer);

      // Update stats
      setStats(prev => ({
        totalQueries: prev.totalQueries + 1,
        totalTime: prev.totalTime + time,
        avgResponseTime: (prev.totalTime + time) / (prev.totalQueries + 1)
      }));

      setQuestion("");

    } catch (error) {

      setAnswer("Error connecting to backend.");

    }

    setLoading(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      askQuestion();
    }
  };

  return (
    <div className="app-wrapper">
      <div className="container">

        <div className="status-strip reveal-0">
          <div className="status-pill">
            <span className="status-dot"></span>
            System Online
          </div>
          <div className="status-pill">
            <span className="status-dot slow"></span>
            Model: Ready
          </div>
          <div className="status-pill">
            {liveTime.toLocaleTimeString()}
          </div>
          <div className="status-pill">
            <span className={`status-dot ${loading ? "busy" : ""}`}></span>
            {loading ? "Processing" : "Idle"}
          </div>
        </div>

        <div className="header reveal-1">
          <div className="logo-section">
            <div className="logo">📡</div>
            <div>
              <div className="title" data-text="RAN Assistant Pro">RAN Assistant Pro</div>
              <div className="subtitle">
                Intelligent Telecom RAN Support System
              </div>
            </div>
          </div>
        </div>

        <div className="stats-dashboard reveal-2">
          <div className="stat-card">
            <div className="stat-label">Total Queries</div>
            <div className="stat-value">{displayedStats.totalQueries}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Avg Response Time</div>
            <div className="stat-value">{displayedStats.avgResponseTime}ms</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Last Response</div>
            <div className="stat-value">{displayedStats.responseTime}ms</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Model</div>
            <div className="stat-value model-name">llama-3.3-70b</div>
          </div>
        </div>

        <div className="input-section reveal-3">
          <label className="input-label">Ask Your Question</label>
          <textarea
            rows="5"
            placeholder="Ask telecom questions like:
• What is 5G RAN?
• Explain network slicing
• How does network densification support 5G?
(Press Ctrl+Enter to submit)"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyPress={handleKeyPress}
            className="input-textarea"
          />

          <div className="button-group">
            <button 
              onClick={askQuestion}
              disabled={loading || !question.trim()}
              className="btn-primary"
            >
              {loading ? "⏳ Generating..." : "🤖 Ask AI"}
            </button>
            <button 
              onClick={() => { setQuestion(""); setAnswer(""); }}
              className="btn-secondary"
            >
              Clear
            </button>
          </div>
        </div>

        {loading && (
          <div className="loading-container reveal-4">
            <div className="spinner"></div>
            <div className="loading-text">Generating Answer...</div>
          </div>
        )}

        {answer && !loading && (
          <div className="answer-section reveal-4">
            <div className="answer-header">
              <span className="answer-icon">✨</span>
              <span>AI Response</span>
              <span className="response-time">Response Time: {displayedStats.responseTime}ms</span>
            </div>
            <div className="answer-box">
              {displayedAnswer}
              {displayedAnswer.length < answer.length && (
                <span className="typing-caret">|</span>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default App;
