import React from 'react';

function SectionCard({ title, subtitle, url, badge, description, verified, is_search_fallback }) {
  const isValidUrl = url && typeof url === 'string' && (url.startsWith('http://') || url.startsWith('https://'));
  const isDirectVerifiedLink = isValidUrl && verified === true && !is_search_fallback;
  const isSearchFallbackLink = isValidUrl && (is_search_fallback === true || verified === false);

  return (
    <div className="section-card">
      <div className="section-card-content">
        <div className="section-card-header">
          <h4 className="section-card-title">{title}</h4>
          {badge && <span className="badge">{badge}</span>}
        </div>
        {subtitle && <p className="section-card-subtitle">Source / Channel: <strong>{subtitle}</strong></p>}
        {description && <p className="section-card-description">{description}</p>}
      </div>

      <div className="section-card-actions">
        {isDirectVerifiedLink && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="link-btn direct-link-btn"
          >
            Open Link →
          </a>
        )}

        {isSearchFallbackLink && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="link-btn fallback-search-btn"
            title="Direct link could not be verified. Click to search online."
          >
            {badge === 'Video' ? 'Search YouTube ↗' : 'Search Resource ↗'}
          </a>
        )}

        {!isValidUrl && (
          <span className="resource-unavailable-tag">
            Resource Unavailable
          </span>
        )}
      </div>
    </div>
  );
}

export default SectionCard;

