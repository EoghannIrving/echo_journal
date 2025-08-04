(function() {
  const cfg = window.ejConfig || {};
  const entryDate = cfg.entryDate || "";
  let currentPrompt = cfg.prompt || "";
  let currentCategory = cfg.category || "";
  let currentAnchor = cfg.anchor || "";
  const promptKey = `ej-prompt-${entryDate}`;
  const readonly = cfg.readonly === true || cfg.readonly === "true";
  const energyLevels = { drained: 1, low: 2, ok: 3, energized: 4 };
  const getEnergyValue = (level) => energyLevels[level] || null;
  const defaultIntegrations = { wordnik: true, immich: true, jellyfin: true, fact: true, ai: true };
  const integrationSettings = { ...defaultIntegrations, ...(cfg.integrations || {}) };

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

      const el = document.getElementById('location-display');
      if (el) {
        el.dataset.lat = latitude;
        el.dataset.lon = longitude;
        el.dataset.accuracy = accuracy;
        el.dataset.locationName = locationLabel;
      }

      const weatherEl = document.getElementById('weather-display');
      if (weatherEl) {
        const weather = await fetchWeather(latitude, longitude);
        if (weather) {
          weatherEl.dataset.temp = weather.temperature;
          weatherEl.dataset.code = weather.code;
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
      target.classList.remove('opacity-0');

      let delay = startDelay;
      const tokens = text.split(/(\s+)/);

      tokens.forEach((token) => {
        if (/^\s+$/.test(token)) {
          setTimeout(() => target.appendChild(document.createTextNode(token)), delay);
          delay += wordDelay;
        } else {
          Array.from(token).forEach((ch) => {
            setTimeout(() => {
              target.textContent += ch;
            }, delay);
            delay += letterDelay;
          });
          delay += wordDelay;
        }
      });

      return delay;
    };

    const welcomeEl = document.getElementById('welcome-message');
    const focusToggle = document.getElementById('focus-toggle');
    const newBtn = document.getElementById('new-prompt');
    const aiBtn = document.getElementById('ai-prompt');
    const restartNotice = document.getElementById('restart-notice');
    if (aiBtn && !integrationSettings.ai) {
      aiBtn.classList.add('hidden');
    }
    const promptSection = document.getElementById('prompt-section');
    const editorSection = document.getElementById('editor-section');
    const moodSelect = document.getElementById('mood-select');
    const energySelect = document.getElementById('energy-select');
    let moodEnergyLocked = false;
    let delay = 0;
    if (restartNotice) {
      const removeNotice = () => restartNotice.remove();
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        restartNotice.classList.remove('opacity-0');
        setTimeout(removeNotice, 7000);
      } else {
        requestAnimationFrame(() => restartNotice.classList.remove('opacity-0'));
        setTimeout(() => {
          restartNotice.classList.add('opacity-0');
          setTimeout(removeNotice, 1000);
        }, 6000);
      }
    }
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
    const anchorEl = document.getElementById('prompt-anchor');
    const textarea = document.getElementById('journal-text');
    const stored = localStorage.getItem(promptKey);
    if (stored) {
      try {
        const data = JSON.parse(stored);
        currentPrompt = data.prompt || currentPrompt;
        currentCategory = data.category || currentCategory;
        currentAnchor = data.anchor || currentAnchor;
      } catch (_) {}
    }
    const revealPrompt = (startDelay = delay + 300) => {
      if (!currentPrompt) return;
      if (promptSection) promptSection.classList.remove('hidden');
      if (promptEl) {
        promptEl.textContent = currentPrompt;
        const totalDelay = animateText(promptEl, startDelay, 15, 40);
        const showEditor = () => {
          if (editorSection) {
            editorSection.classList.remove('hidden');
            if (textarea) textarea.dispatchEvent(new Event('input'));
          }
          const buttons = [newBtn, integrationSettings.ai ? aiBtn : null, focusToggle].filter(Boolean);
          buttons.forEach(btn => btn.classList.remove('hidden'));
        };
        setTimeout(showEditor, totalDelay + 200);
      }
      if (catEl) {
        catEl.textContent = currentCategory || '';
        catEl.classList.toggle('hidden', !currentCategory);
      }
      if (anchorEl) {
        anchorEl.textContent = currentAnchor || '';
        anchorEl.classList.toggle('hidden', !currentAnchor);
      }
    };

    const hasEntryContent = textarea && textarea.value.trim() !== '';
    let promptShown = false;
    if (hasEntryContent) {
      if (moodSelect) moodSelect.disabled = true;
      if (energySelect) energySelect.disabled = true;
      moodEnergyLocked = true;
    }
    const initialMood = moodSelect ? moodSelect.value : '';
    const initialEnergy = energySelect ? energySelect.value : '';
    if (currentPrompt && (hasEntryContent || (initialMood && initialEnergy))) {
      revealPrompt();
      promptShown = true;
    }

    const maybeFetchPrompt = async () => {
      const mood = moodSelect ? moodSelect.value : '';
      const energyStr = energySelect ? energySelect.value : '';
      const energy = getEnergyValue(energyStr);
      // Only fetch when both fields are chosen
      if (!mood || !energy) return;
      // Hide any existing prompt to avoid flashing stale content
      if (promptSection) promptSection.classList.add('hidden');
      if (promptEl) promptEl.textContent = '';
      if (promptEl) promptEl.classList.add('opacity-0');
      if (editorSection) editorSection.classList.add('hidden');
      [newBtn, integrationSettings.ai ? aiBtn : null, focusToggle]
        .filter(Boolean)
        .forEach(btn => btn.classList.add('hidden'));
      try {
        const params = new URLSearchParams({ mood, energy });
        const res = await fetch(`/api/new_prompt?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          currentPrompt = data.prompt;
          currentCategory = data.category || '';
          currentAnchor = data.anchor || '';
          revealPrompt(0);
          promptShown = true;
          localStorage.setItem(promptKey, JSON.stringify({ prompt: currentPrompt, category: currentCategory, anchor: currentAnchor }));
        }
      } catch (_) {}
    };

    if (moodSelect) {
      moodSelect.addEventListener('change', maybeFetchPrompt);
    }
    if (energySelect) {
      energySelect.addEventListener('change', maybeFetchPrompt);
    }
    const params = new URLSearchParams(window.location.search);
    if (params.get('focus') === '1') {
      document.body.classList.add('focus-mode');
    }
    if (focusToggle) {
      const updateLabel = () => {
        const active = document.body.classList.contains('focus-mode');
        focusToggle.textContent = active ? 'Exit Focus' : 'Focus';
        focusToggle.setAttribute('aria-pressed', active ? 'true' : 'false');
      };
      updateLabel();
      focusToggle.addEventListener('click', () => {
        document.body.classList.toggle('focus-mode');
        updateLabel();
      });
    }

    const toolbar = document.getElementById('md-toolbar');
    const saveButton = document.getElementById('save-button');
    if (textarea) {
      // Ensure the field height matches preloaded content
      textarea.dispatchEvent(new Event('input'));
    }
    if (textarea && saveButton) {
      const toggleSaveVisibility = () => {
        saveButton.classList.toggle('hidden', textarea.value.trim() === '');
      };
      toggleSaveVisibility();
      textarea.addEventListener('input', toggleSaveVisibility);
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
    if (newBtn && promptEl) {
      newBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const mood = moodSelect ? moodSelect.value : '';
        const energyStr = energySelect ? energySelect.value : '';
        const energy = getEnergyValue(energyStr);
        const params = new URLSearchParams();
        if (mood) params.append('mood', mood);
        if (energy) params.append('energy', energy);
        const url = `/api/new_prompt${params.toString() ? `?${params.toString()}` : ''}`;
        try {
          const res = await fetch(url);
          if (res.ok) {
            const data = await res.json();
            currentPrompt = data.prompt;
            currentCategory = data.category || '';
            currentAnchor = data.anchor || '';
            promptEl.textContent = currentPrompt;
            if (catEl) {
              catEl.textContent = currentCategory;
              catEl.classList.toggle('hidden', !currentCategory);
            }
            if (anchorEl) {
              anchorEl.textContent = currentAnchor;
              anchorEl.classList.toggle('hidden', !currentAnchor);
            }
            localStorage.setItem(promptKey, JSON.stringify({ prompt: currentPrompt, category: currentCategory, anchor: currentAnchor }));
          }
        } catch (_) {}
      });
    }

    if (aiBtn && promptEl) {
      aiBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        try {
          const res = await fetch('/api/ai_prompt');
          if (res.ok) {
            const data = await res.json();
            currentPrompt = data.prompt;
            currentCategory = '';
            currentAnchor = '';
            promptEl.textContent = currentPrompt;
            if (catEl) {
              catEl.textContent = '';
              catEl.classList.add('hidden');
            }
            if (anchorEl) {
              anchorEl.textContent = '';
              anchorEl.classList.add('hidden');
            }
            localStorage.setItem(promptKey, JSON.stringify({ prompt: currentPrompt, category: currentCategory, anchor: currentAnchor }));
          } else {
            alert('Failed to fetch AI prompt.');
          }
        } catch (_) {}
      });
    }

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
        const weatherEl = document.getElementById('weather-display');
        let weather = null;
        if (weatherEl && weatherEl.dataset.temp && weatherEl.dataset.code) {
          weather = {
            temperature: parseFloat(weatherEl.dataset.temp),
            code: parseInt(weatherEl.dataset.code, 10)
          };
        }
        const mood = moodSelect ? moodSelect.value : '';
        const energy = energySelect ? energySelect.value : '';

        const status = document.getElementById('save-status');
        try {
          const response = await fetch('/entry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, content, prompt, category, location, weather, mood, energy, integrations: integrationSettings })
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
            if (!moodEnergyLocked) {
              if (moodSelect) moodSelect.disabled = true;
              if (energySelect) energySelect.disabled = true;
              moodEnergyLocked = true;
            }
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
