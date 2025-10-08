import React, { useState } from 'react';
import SearchBar from '../components/SearchBar';
import PatentCard from '../components/PatentCard';
import StatsDashboard from '../components/StatsDashboard';
import patentApi from '../services/api';
import './HomePage.css';

const HomePage = () => {
  const [patents, setPatents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchType, setSearchType] = useState('database'); // 'database' or 'uspto'
  const [searchPerformed, setSearchPerformed] = useState(false);

  const handleSearch = async (searchTerm) => {
    try {
      setLoading(true);
      setError(null);
      setSearchPerformed(true);

      let data;
      if (searchType === 'database') {
        // Search existing database
        data = await patentApi.getPatents(searchTerm);
      } else {
        // Search USPTO and optionally store
        const result = await patentApi.searchByIdea(searchTerm, true);
        data = result.patents || [];
      }

      setPatents(data);
    } catch (err) {
      setError('Failed to search patents. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home-page">
      <header className="home-header">
        <h1 className="app-title">Patent Discovery System</h1>
        <p className="app-subtitle">
          Search and explore patents from USPTO database
        </p>
      </header>

      <div className="search-section">
        <div className="search-type-toggle">
          <button
            className={`toggle-btn ${searchType === 'database' ? 'active' : ''}`}
            onClick={() => setSearchType('database')}
          >
            Search Database
          </button>
          <button
            className={`toggle-btn ${searchType === 'uspto' ? 'active' : ''}`}
            onClick={() => setSearchType('uspto')}
          >
            Search USPTO (Live)
          </button>
        </div>

        <SearchBar
          onSearch={handleSearch}
          placeholder={
            searchType === 'database'
              ? 'Search patents in database...'
              : 'Describe your invention idea to search USPTO...'
          }
          isLoading={loading}
        />

        {searchType === 'uspto' && (
          <p className="search-info">
            💡 This will fetch live data from USPTO and store it in the database
          </p>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Searching patents...</p>
        </div>
      )}

      {!loading && searchPerformed && patents.length === 0 && (
        <div className="no-results">
          <p>No patents found. Try a different search term.</p>
        </div>
      )}

      {!loading && patents.length > 0 && (
        <div className="results-section">
          <h2 className="results-title">
            Found {patents.length} patent{patents.length !== 1 ? 's' : ''}
          </h2>
          <div className="patents-list">
            {patents.map((patent) => (
              <PatentCard key={patent.patent_number} patent={patent} />
            ))}
          </div>
        </div>
      )}

      {!searchPerformed && <StatsDashboard />}
    </div>
  );
};

export default HomePage;
