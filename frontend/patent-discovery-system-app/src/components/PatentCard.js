import React from 'react';
import { useNavigate } from 'react-router-dom';
import './PatentCard.css';

const PatentCard = ({ patent }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/patent/${patent.patent_number}`);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const truncateText = (text, maxLength = 200) => {
    if (!text) return 'No abstract available';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="patent-card" onClick={handleClick}>
      <div className="patent-card-header">
        <h3 className="patent-title">{patent.title || 'Untitled Patent'}</h3>
        <span className="patent-number">#{patent.patent_number}</span>
      </div>

      <div className="patent-card-body">
        <p className="patent-abstract">{truncateText(patent.abstract)}</p>

        <div className="patent-card-meta">
          <div className="meta-item">
            <span className="meta-label">Grant Date:</span>
            <span className="meta-value">{formatDate(patent.grant_date)}</span>
          </div>
          {patent.assignee_name && (
            <div className="meta-item">
              <span className="meta-label">Assignee:</span>
              <span className="meta-value">{patent.assignee_name}</span>
            </div>
          )}
        </div>
      </div>

      <div className="patent-card-footer">
        <button className="view-details-btn">View Details →</button>
      </div>
    </div>
  );
};

export default PatentCard;
