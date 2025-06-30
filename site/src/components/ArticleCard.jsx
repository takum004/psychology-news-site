import React from 'react';

const ArticleCard = ({ article }) => {
  const getCategoryColor = (category) => {
    const colors = {
      'Neuroscience': 'bg-purple-100 text-purple-800',
      'Mental Health': 'bg-green-100 text-green-800',
      'Clinical Psychology': 'bg-blue-100 text-blue-800',
      'Cognitive Psychology': 'bg-yellow-100 text-yellow-800',
      'Health Psychology': 'bg-pink-100 text-pink-800',
      'Developmental Psychology': 'bg-indigo-100 text-indigo-800',
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  return (
    <article className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300">
      <div className="aspect-w-16 aspect-h-9">
        <img 
          src={article.image} 
          alt={article.title}
          className="w-full h-48 object-cover"
        />
      </div>
      <div className="p-6">
        <div className="flex items-center justify-between mb-3">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getCategoryColor(article.category)}`}>
            {article.category}
          </span>
          <span className="text-sm text-gray-500">{article.readTime}</span>
        </div>
        <h3 className="text-xl font-bold text-gray-900 mb-2 line-clamp-2">
          {article.title}
        </h3>
        <p className="text-gray-600 mb-4 line-clamp-3">
          {article.excerpt}
        </p>
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            <span className="font-medium">{article.author}</span>
            <span className="mx-2">•</span>
            <time dateTime={article.date}>
              {new Date(article.date).toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </time>
          </div>
          <button className="text-primary-600 hover:text-primary-700 font-semibold text-sm flex items-center group">
            Read more
            <svg 
              className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M9 5l7 7-7 7" 
              />
            </svg>
          </button>
        </div>
      </div>
    </article>
  );
};

export default ArticleCard;