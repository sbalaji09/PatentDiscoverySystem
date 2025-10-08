import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import PatentDetail from './components/PatentDetail';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/patent/:patentNumber" element={<PatentDetail />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
