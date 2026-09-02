import React from 'react';

function SectionCard({ title, subtitle, url, badge, description }) {
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
      {url && (
        <a href={url} target="_blank" rel="noopener noreferrer" className="link-btn">
          Open Link →
        </a>
      )}
    </div>
  );
}

export default SectionCard;
