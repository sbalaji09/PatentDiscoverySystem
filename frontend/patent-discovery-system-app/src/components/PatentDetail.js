import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import patentApi from '../services/api';
import './PatentDetail.css';

const PatentDetail = () => {
  const { patentNumber } = useParams();
  const navigate = useNavigate();
  const [patent, setPatent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPatentDetail = async () => {
      try {
        setLoading(true);
        const data = await patentApi.getPatentDetail(patentNumber);
        setPatent(data);
        setError(null);
      } catch (err) {
        setError('Failed to load patent details. Please try again.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchPatentDetail();
  }, [patentNumber]);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const handleCitationClick = (citedPatentNumber) => {
    navigate(`/patent/${citedPatentNumber}`);
  };

  if (loading) {
    return (
      <div className="patent-detail-container">
        <div className="loading">Loading patent details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="patent-detail-container">
        <div className="error">{error}</div>
        <button onClick={() => navigate('/')} className="back-button">
          ← Back to Search
        </button>
      </div>
    );
  }

  if (!patent) {
    return (
      <div className="patent-detail-container">
        <div className="error">Patent not found</div>
        <button onClick={() => navigate('/')} className="back-button">
          ← Back to Search
        </button>
      </div>
    );
  }

  return (
    <div className="patent-detail-container">
      <button onClick={() => navigate(-1)} className="back-button">
        ← Back
      </button>

      <div className="patent-detail-header">
        <div className="patent-number-badge">Patent #{patent.patent_number}</div>
        <h1 className="patent-detail-title">{patent.title}</h1>
      </div>

      <div className="patent-detail-meta">
        <div className="meta-row">
          <span className="meta-label">Filing Date:</span>
          <span className="meta-value">{formatDate(patent.filing_date)}</span>
        </div>
        <div className="meta-row">
          <span className="meta-label">Grant Date:</span>
          <span className="meta-value">{formatDate(patent.grant_date)}</span>
        </div>
        {patent.assignee_name && (
          <div className="meta-row">
            <span className="meta-label">Assignee:</span>
            <span className="meta-value">{patent.assignee_name}</span>
          </div>
        )}
        {patent.inventor_names && (
          <div className="meta-row">
            <span className="meta-label">Inventors:</span>
            <span className="meta-value">{patent.inventor_names}</span>
          </div>
        )}
      </div>

      {patent.abstract && (
        <div className="patent-section">
          <h2 className="section-title">Abstract</h2>
          <p className="abstract-text">{patent.abstract}</p>
        </div>
      )}

      {patent.claims && patent.claims.length > 0 && (
        <div className="patent-section">
          <h2 className="section-title">Claims ({patent.claims.length})</h2>
          <div className="claims-list">
            {patent.claims.map((claim) => (
              <div key={claim.claim_number} className="claim-item">
                <span className="claim-number">Claim {claim.claim_number}:</span>
                <p className="claim-text">{claim.claim_text}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="citations-container">
        {patent.cited_patents && patent.cited_patents.length > 0 && (
          <div className="patent-section citations-section">
            <h2 className="section-title">
              Backward Citations ({patent.cited_patents.length})
            </h2>
            <p className="citations-description">Patents cited by this patent:</p>
            <div className="citations-list">
              {patent.cited_patents.map((citedPatent, index) => (
                <button
                  key={index}
                  className="citation-link"
                  onClick={() => handleCitationClick(citedPatent)}
                >
                  {citedPatent}
                </button>
              ))}
            </div>
          </div>
        )}

        {patent.citing_patents && patent.citing_patents.length > 0 && (
          <div className="patent-section citations-section">
            <h2 className="section-title">
              Forward Citations ({patent.citing_patents.length})
            </h2>
            <p className="citations-description">Patents that cite this patent:</p>
            <div className="citations-list">
              {patent.citing_patents.map((citingPatent, index) => (
                <button
                  key={index}
                  className="citation-link"
                  onClick={() => handleCitationClick(citingPatent)}
                >
                  {citingPatent}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatentDetail;
