import React from 'react';

function Loader() {
  return (
    <div className="loader-container">
      <div className="spinner"></div>
      <p className="loader-text">Searching the web and building your study pack...</p>
    </div>
  );
}

export default Loader;
