import React, { useState, useEffect } from 'react';
import patentApi from '../services/api';
import './StatsDashboard.css';

const StatsDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await patentApi.getStats();
        setStats(data);
        setError(null);
      } catch (err) {
        setError('Failed to load statistics. Please try again.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="stats-dashboard">
        <div className="loading">Loading statistics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stats-dashboard">
        <div className="error">{error}</div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="stats-dashboard">
      <h2 className="stats-title">Database Statistics</h2>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📄</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_patents.toLocaleString()}</div>
            <div className="stat-label">Total Patents</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📋</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_claims.toLocaleString()}</div>
            <div className="stat-label">Total Claims</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🔗</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_citations.toLocaleString()}</div>
            <div className="stat-label">Total Citations</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <div className="stat-value">{stats.average_claims_per_patent}</div>
            <div className="stat-label">Avg Claims/Patent</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🆕</div>
          <div className="stat-content">
            <div className="stat-value">{stats.recent_patents_1year.toLocaleString()}</div>
            <div className="stat-label">Patents (Last Year)</div>
          </div>
        </div>
      </div>

      {stats.top_assignees && stats.top_assignees.length > 0 && (
        <div className="top-assignees-section">
          <h3 className="section-title">Top Assignees</h3>
          <div className="assignees-list">
            {stats.top_assignees.map((assignee, index) => (
              <div key={index} className="assignee-item">
                <div className="assignee-rank">#{index + 1}</div>
                <div className="assignee-info">
                  <div className="assignee-name">{assignee.assignee_name}</div>
                  <div className="assignee-count">{assignee.patent_count} patents</div>
                </div>
                <div className="assignee-bar">
                  <div
                    className="assignee-bar-fill"
                    style={{
                      width: `${(assignee.patent_count / stats.top_assignees[0].patent_count) * 100}%`
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StatsDashboard;
