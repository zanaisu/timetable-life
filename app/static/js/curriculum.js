/**
 * Curriculum Browser functionality
 */
document.addEventListener('DOMContentLoaded', function() {
  // DOM elements
  const searchInput = document.getElementById('curriculum-search');
  const subjectList = document.getElementById('subject-list');
  const topicsContainer = document.getElementById('topics-container');
  const subtopicsContainer = document.getElementById('subtopics-container');
  
  // Hide any add task button that might have been incorrectly injected
  const addTaskBtn = document.getElementById('add-bonus-task-btn');
  if (addTaskBtn && window.location.pathname.includes('/curriculum')) {
    addTaskBtn.style.display = 'none';
  }
  
  let currentSubjectId = null;
  let currentTopicId = null;
  
  // Cache for confidence data
  const confidenceCache = {
    subtopics: {},
    topics: {}
  };
  
  // Initialize the curriculum browser
  initialize();
  
  function initialize() {
    // Load all confidence data first
    loadAllConfidenceData()
      .then(() => {
        // Then load subjects and their topics/subtopics
        loadSubjects();
        
        // Set up search functionality
        setupSearch();
      })
      .catch(error => {
        console.error('Error initializing confidence data:', error);
        // Continue with loading subjects even if confidence data fails
        loadSubjects();
        setupSearch();
      });
  }
  
  // Load all confidence data
  function loadAllConfidenceData() {
    return fetch('/api/confidence/user/data')
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Cache subtopic confidence
        if (data.subtopic_confidences) {
          data.subtopic_confidences.forEach(item => {
            confidenceCache.subtopics[item.subtopic_id] = item.confidence_level;
          });
        }
        
        // Cache topic confidence
        if (data.topic_confidences) {
          data.topic_confidences.forEach(item => {
            confidenceCache.topics[item.topic_id] = item.confidence_percent;
          });
        }
        
        console.log('Confidence data loaded and cached');
        return confidenceCache;
      })
      .catch(error => {
        console.error('Error loading confidence data:', error);
        // Initialize confidence cache with defaults if loading fails
        return confidenceCache;
      });
  }
  
  // Load all subjects
  function loadSubjects() {
    fetch('/api/curriculum/subjects')
      .then(response => response.json())
      .then(data => {
        if (data.subjects && data.subjects.length > 0) {
          subjectList.innerHTML = '';
          
          data.subjects.forEach(subject => {
            const subjectElement = document.createElement('li');
            subjectElement.className = 'subject-item';
            subjectElement.dataset.id = subject.id;
            
            subjectElement.innerHTML = `
              <div class="subject-header">
                <span class="subject-title">${subject.title}</span>
                <span class="subject-count">${subject.topic_count} topics</span>
              </div>
            `;
            
            subjectList.appendChild(subjectElement);
          });
          
          // Add click handler for subjects
          document.querySelectorAll('.subject-item').forEach(item => {
            item.addEventListener('click', handleSubjectClick);
          });
        } else {
          subjectList.innerHTML = '<li class="empty-state">No subjects found</li>';
        }
      })
      .catch(error => {
        console.error('Error loading subjects:', error);
        subjectList.innerHTML = '<li class="empty-state">Error loading subjects</li>';
      });
  }
  
  // Subject click handler
  function handleSubjectClick(e) {
    const subjectItem = e.currentTarget;
    const subjectId = subjectItem.dataset.id;
    
    // Deselect any previously selected subject
    document.querySelectorAll('.subject-item.selected').forEach(item => {
      item.classList.remove('selected');
    });
    
    // Select the new subject
    subjectItem.classList.add('selected');
    currentSubjectId = subjectId;
    
    // Load topics for this subject
    loadTopics(currentSubjectId);
    
    // Clear subtopics
    subtopicsContainer.innerHTML = '<p class="empty-state">Select a topic to view subtopics</p>';
  }
  
  // Load topics for a subject and also load all subtopics immediately
  function loadTopics(subjectId) {
    console.log(`Loading topics for subject ${subjectId}`);
    // Clear subtopics first
    subtopicsContainer.innerHTML = '<p class="loading-state">Loading all subtopics...</p>';
    
    fetch(`/api/curriculum/subject/${subjectId}/topics`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.topics && data.topics.length > 0) {
          topicsContainer.innerHTML = '';
          
          // Store all topics to load their subtopics
          const topicPromises = [];
          
          data.topics.forEach(topic => {
            const topicElement = document.createElement('div');
            topicElement.className = 'topic-item';
            topicElement.dataset.id = topic.id;
            
            // Get topic confidence from cache or default to 50%
            const topicConfidence = confidenceCache.topics[topic.id] || 50;
            
            // Determine the confidence color class
            const confidenceColorClass = getConfidenceColorClass(topicConfidence);
            
            // Create the HTML structure with topic confidence bar
            topicElement.innerHTML = `
              <div class="topic-header">
                <span class="topic-title">${topic.title}</span>
                <span class="topic-count">${topic.subtopics_count} subtopics</span>
              </div>
              <p class="topic-description">${topic.description || ''}</p>
              <div class="topic-confidence-container">
                <div class="topic-confidence-label">
                  <span>Topic Confidence</span>
                  <span class="topic-confidence-value">${Math.round(topicConfidence)}</span>%
                </div>
                <div class="topic-confidence-bar-container">
                  <div class="topic-confidence-bar ${confidenceColorClass}" style="width: ${topicConfidence}%"></div>
                </div>
              </div>
              <div class="topic-subtopics-container" data-topic-id="${topic.id}"></div>
            `;
            
            topicsContainer.appendChild(topicElement);
            
            // Queue this topic's subtopics to load
            topicPromises.push(loadSubtopicsForTopic(topic.id));
          });
          
          // Add click handler for topics - now just for selection, not loading
          document.querySelectorAll('.topic-item').forEach(item => {
            item.addEventListener('click', handleTopicClick);
          });
          
          // Load all subtopics for all topics
          Promise.all(topicPromises)
            .then(() => {
              console.log('All subtopics loaded successfully');
              subtopicsContainer.innerHTML = '<p class="success-state">All subtopics loaded. Click on a topic to view its subtopics.</p>';
            })
            .catch(error => {
              console.error('Error loading subtopics:', error);
              subtopicsContainer.innerHTML = '<p class="error-state">Error loading some subtopics. Please try again.</p>';
            });
        } else {
          topicsContainer.innerHTML = '<p class="empty-state">No topics found for this subject</p>';
          subtopicsContainer.innerHTML = '<p class="empty-state">No topics available</p>';
        }
      })
      .catch(error => {
        console.error('Error loading topics:', error);
        topicsContainer.innerHTML = '<p class="empty-state">Error loading topics</p>';
        subtopicsContainer.innerHTML = '<p class="empty-state">Error loading content</p>';
      });
  }
  
  // Load subtopics for a topic and store them in topic container
  function loadSubtopicsForTopic(topicId) {
    console.log(`Loading subtopics for topic ${topicId}`);
    return fetch(`/api/curriculum/topic/${topicId}/subtopics`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.subtopics && data.subtopics.length > 0) {
          // Find the container for this topic's subtopics
          const container = document.querySelector(`.topic-subtopics-container[data-topic-id="${topicId}"]`);
          if (!container) {
            console.error(`Subtopic container for topic ${topicId} not found`);
            return;
          }
          
          // Create a fragment to hold all subtopics
          const fragment = document.createDocumentFragment();
          
          data.subtopics.forEach(subtopic => {
            const subtopicElement = document.createElement('div');
            subtopicElement.className = 'subtopic-item hidden'; // Initially hidden
            subtopicElement.dataset.id = subtopic.id;
            subtopicElement.dataset.topicId = topicId;
            
            // Get confidence level for this subtopic (default to 3)
            const confidenceLevel = confidenceCache.subtopics[subtopic.id] || 3;
            
            subtopicElement.innerHTML = `
              <div class="subtopic-header">
                <span class="subtopic-title">${subtopic.title}</span>
              </div>
              <p class="subtopic-description">${subtopic.description || ''}</p>
              <p class="estimated-duration">Estimated Duration: ${subtopic.estimated_duration || 15} min</p>
              
              <!-- Confidence selector -->
              <div class="subtopic-confidence-container">
                <span class="confidence-label">Confidence: <span class="confidence-value">${confidenceLevel}</span>/5</span>
                <div class="confidence-buttons" data-subtopic-id="${subtopic.id}">
                  <button class="confidence-btn" data-level="1" title="Very Low Confidence" ${confidenceLevel === 1 ? 'aria-selected="true"' : ''}></button>
                  <button class="confidence-btn" data-level="2" title="Low Confidence" ${confidenceLevel === 2 ? 'aria-selected="true"' : ''}></button>
                  <button class="confidence-btn" data-level="3" title="Medium Confidence" ${confidenceLevel === 3 ? 'aria-selected="true"' : ''}></button>
                  <button class="confidence-btn" data-level="4" title="High Confidence" ${confidenceLevel === 4 ? 'aria-selected="true"' : ''}></button>
                  <button class="confidence-btn" data-level="5" title="Very High Confidence" ${confidenceLevel === 5 ? 'aria-selected="true"' : ''}></button>
                </div>
              </div>
            `;
            
            fragment.appendChild(subtopicElement);
          });
          
          // Add all subtopics to the container
          container.appendChild(fragment);
          
          // Add event listeners to confidence buttons
          container.querySelectorAll('.confidence-buttons').forEach(buttonContainer => {
            buttonContainer.addEventListener('click', handleConfidenceButtonClick);
          });
          
          return data.subtopics;
        }
        return [];
      })
      .catch(error => {
        console.error(`Error loading subtopics for topic ${topicId}:`, error);
        throw error;
      });
  }
  
  // Topic click handler - just shows/hides the associated subtopics
  function handleTopicClick(e) {
    const topicItem = e.currentTarget;
    const topicId = topicItem.dataset.id;
    
    // Deselect any previously selected topic
    document.querySelectorAll('.topic-item.selected').forEach(item => {
      item.classList.remove('selected');
    });
    
    // Select the new topic
    topicItem.classList.add('selected');
    currentTopicId = topicId;
    
    // Hide all subtopics first
    document.querySelectorAll('.subtopic-item').forEach(item => {
      item.classList.add('hidden');
    });
    
    // Show only the subtopics for this topic
    document.querySelectorAll(`.subtopic-item[data-topic-id="${topicId}"]`).forEach(item => {
      item.classList.remove('hidden');
    });
    
    // Update the subtopics panel title
    const topicTitle = topicItem.querySelector('.topic-title').textContent;
    subtopicsContainer.innerHTML = `
      <h3 class="selected-topic-title">${topicTitle} Subtopics</h3>
      <div id="current-subtopics-container"></div>
    `;
    
    // Move relevant subtopics to the subtopics panel for better visibility
    const currentSubtopicsContainer = document.getElementById('current-subtopics-container');
    document.querySelectorAll(`.subtopic-item[data-topic-id="${topicId}"]`).forEach(item => {
      const clone = item.cloneNode(true);
      clone.classList.remove('hidden');
      currentSubtopicsContainer.appendChild(clone);
    });
    
    // Add event listeners to confidence buttons in the cloned elements
    currentSubtopicsContainer.querySelectorAll('.confidence-buttons').forEach(buttonContainer => {
      buttonContainer.addEventListener('click', handleConfidenceButtonClick);
    });
  }
  
  // Handle confidence button click
  function handleConfidenceButtonClick(e) {
    if (!e.target.classList.contains('confidence-btn')) return;
    
    const confidenceLevel = parseInt(e.target.dataset.level);
    const buttonsContainer = e.currentTarget;
    const subtopicId = buttonsContainer.dataset.subtopicId;
    const subtopicElement = buttonsContainer.closest('.subtopic-item');
    const topicId = subtopicElement.dataset.topicId;
    
    // Update visual state for all instances of this subtopic
    document.querySelectorAll(`.confidence-buttons[data-subtopic-id="${subtopicId}"]`).forEach(container => {
      // Remove selected state from all buttons
      container.querySelectorAll('.confidence-btn').forEach(btn => {
        btn.removeAttribute('aria-selected');
      });
      
      // Select the clicked level button
      container.querySelector(`.confidence-btn[data-level="${confidenceLevel}"]`).setAttribute('aria-selected', 'true');
      
      // Update the text display
      const valueElement = container.closest('.subtopic-confidence-container').querySelector('.confidence-value');
      if (valueElement) {
        valueElement.textContent = confidenceLevel;
      }
    });
    
    // Update in database and cache
    updateSubtopicConfidence(subtopicId, confidenceLevel, topicId);
  }
  
  // Update subtopic confidence
  function updateSubtopicConfidence(subtopicId, confidenceLevel, topicId) {
    // Update cache immediately for responsive UI
    confidenceCache.subtopics[subtopicId] = confidenceLevel;
    
    // Send update to server
    fetch(`/api/confidence/user/subtopic/${subtopicId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ confidence_level: confidenceLevel })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to update confidence');
      }
      return response.json();
    })
    .then(data => {
      // Update topic confidence if returned in response
      if (data.topic_confidence) {
        const topicConfidence = data.topic_confidence.confidence_percent;
        confidenceCache.topics[topicId] = topicConfidence;
        
        // Update all instances of this topic's confidence bar
        updateTopicConfidenceDisplay(topicId, topicConfidence);
      }
    })
    .catch(error => {
      console.error('Error updating confidence:', error);
      // Could revert UI here if needed
    });
  }
  
  // Update topic confidence display
  function updateTopicConfidenceDisplay(topicId, confidencePercent) {
    // Find all topic elements with this ID
    document.querySelectorAll(`.topic-item[data-id="${topicId}"]`).forEach(topicElement => {
      const confidenceBar = topicElement.querySelector('.topic-confidence-bar');
      const confidenceValue = topicElement.querySelector('.topic-confidence-value');
      
      if (!confidenceBar || !confidenceValue) return;
      
      // Update the value text
      confidenceValue.textContent = Math.round(confidencePercent);
      
      // Update color class
      confidenceBar.className = 'topic-confidence-bar ' + getConfidenceColorClass(confidencePercent);
      
      // Animate width change - first reset to 0 for better animation
      confidenceBar.style.width = '0%';
      
      // Force a reflow to ensure animation works
      void confidenceBar.offsetWidth;
      
      // Set new width
      requestAnimationFrame(() => {
        confidenceBar.style.width = `${confidencePercent}%`;
      });
    });
  }
  
  // Get color class based on confidence percentage
  function getConfidenceColorClass(confidencePercent) {
    if (confidencePercent >= 100) return 'confidence-100';
    if (confidencePercent >= 80) return 'confidence-80-100';
    if (confidencePercent >= 60) return 'confidence-60-80';
    if (confidencePercent >= 40) return 'confidence-40-60';
    if (confidencePercent >= 20) return 'confidence-20-40';
    return 'confidence-0-20';
  }
  
  // Set up search functionality
  function setupSearch() {
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
      const query = this.value.trim();
      
      if (query.length < 2) {
        // If query is too short, reset to normal view
        document.querySelectorAll('.subject-item').forEach(item => {
          item.style.display = '';
        });
        
        document.querySelectorAll('.topic-item').forEach(item => {
          item.style.display = '';
        });
        
        document.querySelectorAll('.subtopic-item').forEach(item => {
          item.style.display = '';
        });
        return;
      }
      
      fetch(`/api/curriculum/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
          if (!data.results) return;
          
          const results = data.results;
          
          // Filter subjects
          document.querySelectorAll('.subject-item').forEach(item => {
            const subjectId = item.dataset.id;
            const matchingSubject = results.subjects.some(s => s.id.toString() === subjectId);
            const hasMatchingTopic = results.topics.some(t => t.subject_id.toString() === subjectId);
            
            if (matchingSubject || hasMatchingTopic) {
              item.style.display = '';
            } else {
              item.style.display = 'none';
            }
          });
          
          // If a subject is currently selected, filter its topics
          if (currentSubjectId) {
            document.querySelectorAll('.topic-item').forEach(item => {
              const topicId = item.dataset.id;
              const matchingTopic = results.topics.some(t => t.id.toString() === topicId);
              const hasMatchingSubtopic = results.subtopics.some(st => st.topic_id.toString() === topicId);
              
              if (matchingTopic || hasMatchingSubtopic) {
                item.style.display = '';
              } else {
                item.style.display = 'none';
              }
            });
          }
          
          // If a topic is currently selected, filter its subtopics
          if (currentTopicId) {
            document.querySelectorAll('.subtopic-item').forEach(item => {
              const subtopicId = item.dataset.id;
              const matchingSubtopic = results.subtopics.some(st => st.id.toString() === subtopicId);
              
              if (matchingSubtopic) {
                item.style.display = '';
              } else {
                item.style.display = 'none';
              }
            });
          }
        })
        .catch(error => {
          console.error('Error searching curriculum:', error);
        });
    });
  }
});
