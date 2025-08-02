(function() {
  const cfg = window.ejConfig || {};
  const entryDate = cfg.entryDate || "";
  let currentPrompt = cfg.prompt || "";
  let currentCategory = cfg.category || "";
  const promptKey = `ej-prompt-${entryDate}`;
  const readonly = cfg.readonly === true || cfg.readonly === "true";

  async function fetchWeather(lat, lon) {
    try {
      const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
      if (!res.ok) return null;
      const data = await res.json();
      const cw = data.current_weather;
      if (!cw) return null;
      return { temperature: cw.temperature, code: cw.weathercode };
    } catch (e) {
      console.warn('Weather fetch failed:', e);
      return null;
    }
  }

  const weatherIcons = {
    0: '☀️',        // Clear
    1: '🌤️',       // Mostly clear
    2: '⛅',        // Partly cloudy
    3: '☁️',        // Overcast
    45: '🌫️',      // Fog
    48: '🌫️',      // Fog
    51: '🌦️',      // Drizzle
    53: '🌦️',      // Drizzle
    55: '🌦️',      // Drizzle
    61: '🌧️',      // Rain
    63: '🌧️',      // Rain
    65: '🌧️',      // Heavy rain
    71: '❄️',       // Snow
    73: '❄️',       // Snow
    75: '❄️',       // Snow
    80: '🌦️',      // Showers
    81: '🌦️',      // Showers
    82: '🌧️',      // Heavy showers
    95: '⛈️',      // Thunderstorm
    96: '⛈️',      // Thunderstorm
    99: '⛈️'       // Thunderstorm
  };

  async function fetchGeolocationDetails() {
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(async (pos) => {
      const { latitude, longitude, accuracy } = pos.coords;
      let locationLabel = `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;

      // Try to reverse geocode
      try {
        const res = await fetch(`/api/reverse_geocode?lat=${latitude}&lon=${longitude}`);
        if (res.ok) {
          const data = await res.json();
          locationLabel = data.city || data.region || data.country || data.display_name || locationLabel;
        }
      } catch (e) {
        console.warn('Reverse geocoding failed:', e);
      }

      const detailsEl = document.getElementById('meta-details');
      const el = document.getElementById('location-display');
      if (el) {
        el.textContent = `📍 ${locationLabel} (±${Math.round(accuracy)}m)`;
        el.dataset.lat = latitude;
        el.dataset.lon = longitude;
        el.dataset.accuracy = accuracy;
        el.dataset.locationName = locationLabel;
        el.classList.remove('hidden');
        detailsEl?.classList.remove('hidden');
      }

      const weatherEl = document.getElementById('weather-display');
      if (weatherEl) {
        const weather = await fetchWeather(latitude, longitude);
        if (weather) {
          const icon = weatherIcons[weather.code] || '';
          weatherEl.textContent = `${icon} ${weather.temperature}\u00B0C`.trim();
          weatherEl.classList.remove('hidden');
          detailsEl?.classList.remove('hidden');
        }
      }
    },
    (err) => {
      console.warn('Geolocation permission denied or failed:', err);
    },
    { enableHighAccuracy: true, timeout: 5000 });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const animateText = (target, startDelay = 0, letterDelay = 80, wordDelay = 150) => {
      if (!target) return 0;
      const text = target.textContent.trim();

      // Respect user's reduced motion preference by skipping animation
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        target.textContent = text;
        target.classList.remove('opacity-0');
        return startDelay;
      }

      target.textContent = '';

      let delay = startDelay;
      const tokens = text.split(/(\s+)/);

      tokens.forEach((token) => {
        if (/^\s+$/.test(token)) {
          target.appendChild(document.createTextNode(token));
          return;
        }

        const wordSpan = document.createElement('span');
        wordSpan.style.whiteSpace = 'nowrap';
        wordSpan.style.display = 'inline-block';

        Array.from(token).forEach((ch) => {
          const letter = document.createElement('span');
          letter.textContent = ch;
          letter.className = 'letter-span inline-block opacity-0 transition-opacity duration-200';
          letter.style.transitionDelay = `${delay}ms`;
          delay += letterDelay;
          wordSpan.appendChild(letter);
        });

        delay += wordDelay;
        target.appendChild(wordSpan);
      });

      target.classList.remove('opacity-0');
      requestAnimationFrame(() => {
        target.querySelectorAll('.letter-span').forEach((span) => span.classList.add('opacity-100'));
      });

      return delay;
    };

    const welcomeEl = document.getElementById('welcome-message');
    let delay = 0;
    if (welcomeEl) {
      const wantsGreeting = welcomeEl.dataset.dynamicGreeting === 'true';

      if (wantsGreeting) {
        const hour = new Date().getHours();
        let greeting = '';

        if (hour < 12) greeting = '☀️ Good morning.';
        else if (hour < 18) greeting = '🌿 Good afternoon.';
        else greeting = '🌙 Good evening.';

        welcomeEl.textContent = greeting;
      }

      delay = animateText(welcomeEl, 0, 60, 200);
    }

    const promptEl = document.getElementById('daily-prompt');
    const catEl = document.getElementById('prompt-category');
    const stored = localStorage.getItem(promptKey);
    if (stored) {
      try {
        const data = JSON.parse(stored);
        currentPrompt = data.prompt || currentPrompt;
        currentCategory = data.category || currentCategory;
      } catch (_) {}
    }
    if (promptEl) {
      promptEl.textContent = currentPrompt;
      animateText(promptEl, delay + 300, 15, 40);
    }
    if (catEl) {
      catEl.textContent = currentCategory || '';
      catEl.classList.toggle('hidden', !currentCategory);
    }

    const toolbar = document.getElementById('md-toolbar');
    const textarea = document.getElementById('journal-text');
    if (textarea) {
      // Ensure the field height matches preloaded content
      textarea.dispatchEvent(new Event('input'));
    }
    if (toolbar && textarea) {
      toolbar.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = textarea.value;

        const wrap = (token) => {
          const selected = text.slice(start, end);
          const result = text.slice(0, start) + token + selected + token + text.slice(end);
          textarea.value = result;
          textarea.selectionStart = start + token.length;
          textarea.selectionEnd = end + token.length;
        };

        const prefixLines = (prefix) => {
          const before = text.slice(0, start);
          const selection = text.slice(start, end);
          const after = text.slice(end);
          const lines = selection.split(/\n/);
          const formatted = lines.map(line => prefix + line).join('\n');
          textarea.value = before + formatted + after;
          textarea.selectionStart = start;
          textarea.selectionEnd = start + formatted.length;
        };

        if (action === 'bold') wrap('**');
        else if (action === 'italic') wrap('_');
        else if (action === 'header') prefixLines('# ');
        else if (action === 'list') prefixLines('- ');

        textarea.focus();
        textarea.dispatchEvent(new Event('input'));
      });
    }

    const newBtn = document.getElementById('new-prompt');
    if (newBtn && promptEl) {
      newBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        try {
          const res = await fetch('/api/new_prompt');
          if (res.ok) {
            const data = await res.json();
            currentPrompt = data.prompt;
            currentCategory = data.category || '';
            promptEl.textContent = currentPrompt;
            if (catEl) {
              catEl.textContent = currentCategory;
              catEl.classList.toggle('hidden', !currentCategory);
            }
            localStorage.setItem(promptKey, JSON.stringify({ prompt: currentPrompt, category: currentCategory }));
          }
        } catch (_) {}
      });
    }

    const saveButton = document.getElementById('save-button');
    if (saveButton) {
      saveButton.addEventListener('click', async () => {
        if (saveButton.disabled) {
          return;
        }
        saveButton.disabled = true;
        const content = document.getElementById('journal-text').value;
        const date = entryDate;
        const prompt = currentPrompt;
        const category = currentCategory;
        const locEl = document.getElementById('location-display');
        let location = null;
        if (locEl && locEl.dataset.lat && locEl.dataset.lon) {
          location = {
            lat: parseFloat(locEl.dataset.lat),
            lon: parseFloat(locEl.dataset.lon),
            accuracy: parseFloat(locEl.dataset.accuracy || 0),
            label: locEl.dataset.locationName || ''
          };
        }
        const mood = document.getElementById('mood-select').value;
        const energy = document.getElementById('energy-select').value;

        const status = document.getElementById('save-status');
        try {
          const response = await fetch('/entry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, content, prompt, category, location, mood, energy })
          });

          if (!response.ok) {
            status.textContent = 'Save failed. Server error.';
            status.classList.add('error-text');
            saveButton.disabled = false;
            return;
          }

          const result = await response.json();
          if (result.status === 'success') {
            status.textContent = 'Last saved: just now — Echo Journal';
            status.classList.remove('error-text');
          } else {
            status.textContent = 'Save failed. Please try again.';
            status.classList.add('error-text');
          }
        } catch (err) {
          status.textContent = 'Save failed. Network error.';
          status.classList.add('error-text');
        }
        saveButton.disabled = false;
      });
    }

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (saveButton && !saveButton.disabled) {
          saveButton.click();
        }
      }
    });

    if (!readonly) {
      fetchGeolocationDetails();
    }
  });
})();
