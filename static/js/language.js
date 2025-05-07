// Global language switcher functionality

const supportedLanguages = {
    'en': {
        name: 'English',
        nativeName: 'English',
        noTranslate: true
    },
    'ta': {
        name: 'Tamil',
        nativeName: 'தமிழ்',
        noTranslate: true
    },
    'ml': {
        name: 'Malayalam',
        nativeName: 'മലയാളം',
        noTranslate: true
    },
    'fr': {
        name: 'French',
        nativeName: 'Français',
        noTranslate: true
    },
    'es': {
        name: 'Spanish',
        nativeName: 'Español',
        noTranslate: true
    },
    'de': {
        name: 'German',
        nativeName: 'Deutsch',
        noTranslate: true
    },
    'ja': {
        name: 'Japanese',
        nativeName: '日本語',
        noTranslate: true
    },
    'ko': {
        name: 'Korean',
        nativeName: '한국어',
        noTranslate: true
    },
    'zh': {
        name: 'Chinese',
        nativeName: '中文',
        noTranslate: true
    },
    'hi': {
        name: 'Hindi',
        nativeName: 'हिन्दी',
        noTranslate: true
    },
    'te': {
        name: 'Telugu',
        nativeName: 'తెలుగు',
        noTranslate: true
    }
};

// Initialize language based on localStorage or default to English
document.addEventListener('DOMContentLoaded', function() {
    console.log("Language.js loaded - initializing language switcher");
    
    // Create and inject the language selector into the navbar
    injectLanguageSelector();
    
    // Apply stored language preference or set default
    const currentLang = localStorage.getItem('preferredLanguage') || 'en';
    updateLanguageSelector(currentLang);
    
    // If not English, translate the page
    if (currentLang !== 'en') {
        translatePage(currentLang);
    }
});

// Updated injectLanguageSelector function
function injectLanguageSelector() {
    const navbarLinks = document.querySelector('.navbar-links');
    
    if (!navbarLinks) {
        console.error("Navbar links element not found");
        return;
    }
    
    // Create language selector container
    const langContainer = document.createElement('li');
    langContainer.className = 'lang-nav-container no-translate';
    
    // Create language selector
    const langSelector = document.createElement('select');
    langSelector.id = 'global-lang-selector';
    langSelector.className = 'global-lang-selector no-translate';
    
    // Add language options with only native names
    Object.entries(supportedLanguages).forEach(([code, langData]) => {
        const option = document.createElement('option');
        option.value = code;
        option.textContent = langData.nativeName;
        option.className = 'no-translate';
        langSelector.appendChild(option);
    });
    
    // Add event listener for language change
    langSelector.addEventListener('change', function() {
        const selectedLang = this.value;
        localStorage.setItem('preferredLanguage', selectedLang);
        updateLanguageSelector(selectedLang);
        
        if (selectedLang === 'en') {
            window.location.reload();
        } else {
            translatePage(selectedLang);
        }
    });
    
    // Add selector to container
    langContainer.appendChild(langSelector);
    
    // Add container to navbar
    navbarLinks.appendChild(langContainer);
    console.log("Language selector injected into navbar");
}

// Update language selector value
function updateLanguageSelector(lang) {
    const langSelector = document.getElementById('global-lang-selector');
    if (langSelector && langSelector.value !== lang) {
        langSelector.value = lang;
        console.log(`Updated selector to ${lang}`);
    }
}

// Translate all page content
function translatePage(targetLang) {
    // Show loading indicator
    showTranslationProgress();
    console.log(`Translating page to ${targetLang}`);
    
    // Get all translatable elements
    const elements = getTranslatableElements();
    const totalElements = elements.length;
    console.log(`Found ${totalElements} elements to translate`);
    let completedElements = 0;
    
    // Process elements in batches to avoid API limits and UI freezing
    const batchSize = 5; // Smaller batch size to avoid API issues
    const batches = Math.ceil(totalElements / batchSize);
    
    // Translate in batches
    for (let i = 0; i < batches; i++) {
        const start = i * batchSize;
        const end = Math.min(start + batchSize, totalElements);
        const batch = elements.slice(start, end);
        
        setTimeout(() => {
            processBatch(batch, targetLang, () => {
                completedElements += batch.length;
                updateProgress(completedElements, totalElements);
                
                if (completedElements >= totalElements) {
                    hideTranslationProgress();
                }
            });
        }, i * 1500); // Longer delay (1.5 seconds) between batches to prevent rate limiting
    }
}

// Add MutationObserver to handle dynamic content
let observer = new MutationObserver((mutations) => {
    const currentLang = localStorage.getItem('preferredLanguage');
    if (currentLang && currentLang !== 'en') {
        mutations.forEach((mutation) => {
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // ELEMENT_NODE
                        const elements = getTranslatableElements([node]);
                        if (elements.length > 0) {
                            translateElements(elements, currentLang);
                        }
                    }
                });
            }
        });
    }
});

// Start observing the document with the configured parameters
observer.observe(document.body, { childList: true, subtree: true });

// Update getTranslatableElements to accept optional root element
function getTranslatableElements(roots = [document.body]) {
    const excludeSelectors = [
        '.navbar-brand',
        '.navbar-links a',
        '.navbar-links li',
        '.global-lang-selector',
        '.lang-nav-container',
        '.no-translate'
    ].join(', ');
    
    const selectors = [
        'h1:not(.no-translate)', 
        'h2:not(.no-translate)', 
        'h3:not(.no-translate)', 
        'p:not(.no-translate)', 
        'a:not(.no-translate)', 
        'button:not(.no-translate)', 
        'li:not(.no-translate)',
        '.place-name',
        '.description:not(.no-translate)',
        '.place-card-content h3',
        '.place-description',
        '.feature-title',
        '.feature-description'
    ];
    
    const elements = [];
    roots.forEach(root => {
        selectors.forEach(selector => {
            root.querySelectorAll(selector).forEach(el => {
                // Skip excluded elements and their children
                if (!el.closest(excludeSelectors) && 
                    el.innerText && 
                    el.innerText.trim() !== '' && 
                    !el.hasAttribute('data-translating')) {
                    
                    // Store original text if not already stored
                    if (!el.dataset.originalText) {
                        el.dataset.originalText = el.innerText;
                    }
                    
                    el.setAttribute('data-translating', 'true');
                    elements.push(el);
                }
            });
        });
    });
    
    return elements;
}

// Process a batch of elements for translation
function processBatch(elements, targetLang, callback) {
    if (elements.length === 0) {
        if (callback) callback();
        return;
    }
    
    // Group texts for batch translation
    const textsToTranslate = elements.map(el => el.dataset.originalText);
    const batchText = textsToTranslate.join('\n|||\n');
    
    console.log(`Processing batch of ${elements.length} elements`);
    
    // Use individual translations for better reliability
    let completedCount = 0;
    
    elements.forEach((el, index) => {
        const textToTranslate = el.dataset.originalText;
        
        // Individual translation for each element
        fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                text: textToTranslate,
                language: targetLang
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.translated_text) {
                el.innerText = data.translated_text;
            }
            
            // Remove the processing marker
            el.removeAttribute('data-translating');
            
            // Track completion
            completedCount++;
            if (completedCount === elements.length && callback) {
                callback();
            }
        })
        .catch(error => {
            console.error('Translation error:', error);
            
            // Remove the processing marker
            el.removeAttribute('data-translating');
            
            // Track completion even on error
            completedCount++;
            if (completedCount === elements.length && callback) {
                callback();
            }
        });
    });
}

// Add function to translate specific elements
function translateElements(elements, targetLang) {
    elements.forEach(el => {
        const textToTranslate = el.dataset.originalText;
        
        fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                text: textToTranslate,
                language: targetLang
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.translated_text) {
                el.innerText = data.translated_text;
            }
            el.removeAttribute('data-translating');
        })
        .catch(error => {
            console.error('Translation error:', error);
            el.removeAttribute('data-translating');
        });
    });
}

// Show translation progress indicator
function showTranslationProgress() {
    let progressContainer = document.getElementById('translation-progress');
    
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'translation-progress';
        progressContainer.className = 'translation-progress';
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        
        const progressText = document.createElement('div');
        progressText.className = 'progress-text';
        progressText.innerText = 'Translating...';
        
        progressContainer.appendChild(progressBar);
        progressContainer.appendChild(progressText);
        document.body.appendChild(progressContainer);
    }
    
    progressContainer.style.display = 'flex';
}

// Update translation progress
function updateProgress(completed, total) {
    const progressContainer = document.getElementById('translation-progress');
    if (!progressContainer) return;
    
    const progressBar = progressContainer.querySelector('.progress-bar');
    const progressText = progressContainer.querySelector('.progress-text');
    
    const percent = Math.min(100, Math.round((completed / total) * 100));
    progressBar.style.width = `${percent}%`;
    progressText.innerText = `Translating... ${percent}%`;
}

// Hide translation progress indicator
function hideTranslationProgress() {
    const progressContainer = document.getElementById('translation-progress');
    if (progressContainer) {
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 1000); // Show completion for 1 second
    }
}

// Function to translate individual elements (for use in specific components)
function translateText(index) {
    let descElement = document.getElementById("desc-" + index);
    let text = descElement.dataset.originalText;
    let lang = document.querySelectorAll(".lang-selector")[index - 1].value;

    // Show loading indication
    descElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';

    fetch('/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text, language: lang })
    })
    .then(response => response.json())
    .then(data => {
        descElement.innerText = data.translated_text || "Translation error!";
    })
    .catch(error => {
        descElement.innerText = "Translation failed. Please try again.";
        console.error("Translation error:", error);
    });
}
