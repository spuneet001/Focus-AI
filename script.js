let selectedRating = 0;
const responsesApiUrl = '/api/responses';
let responsesCache = [];

initResponsesLoginPage();

function selectRating(value) {
  selectedRating = value;
  const ratingInput = document.getElementById('fb-rating');

  if (ratingInput) {
    ratingInput.value = String(value);
  }

  document.querySelectorAll('.rating-btn').forEach((button, index) => {
    button.classList.toggle('selected', index < value);
  });
}

async function submitFeedback(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const name = document.getElementById('fb-name');
  const email = document.getElementById('fb-email');
  const message = document.getElementById('fb-message');
  const app = document.getElementById('fb-app');
  const type = document.getElementById('fb-type');
  const successMessage = document.getElementById('success-msg');
  const ratingInput = document.getElementById('fb-rating');
  const submitButton = form ? form.querySelector('.submit-btn') : null;

  if (!form || !name || !email || !message) {
    return;
  }

  if (!name.value.trim() || !email.value.trim() || !message.value.trim()) {
    showFeedbackStatus('Please fill in your name, email, and message.', true);
    return;
  }

  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = 'Saving...';
  }

  try {
    const response = await fetch(responsesApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
      name: name.value.trim(),
      email: email.value.trim(),
      app: app ? app.value : '',
      feedbackType: type ? type.value : '',
      rating: selectedRating > 0 ? String(selectedRating) : '',
      message: message.value.trim(),
      submittedAt: new Date().toISOString(),
      }),
    });

    if (!response.ok) {
      throw new Error('Could not save response');
    }

    showFeedbackStatus('Your feedback was saved successfully.', false);
    form.reset();

    if (ratingInput) {
      ratingInput.value = '';
    }

    selectedRating = 0;
    document.querySelectorAll('.rating-btn').forEach((button) => {
      button.classList.remove('selected');
    });

    window.setTimeout(() => {
      successMessage.classList.remove('show');
      successMessage.classList.remove('is-error');
    }, 5000);
  } catch (error) {
    showFeedbackStatus('The response could not be saved. Start the Python backend server and try again.', true);
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = 'Send Feedback →';
    }
  }
}

async function renderResponses() {
  const responsesList = document.getElementById('responses-list');
  const emptyState = document.getElementById('responses-empty');
  const tableWrap = document.getElementById('responses-table-wrap');
  const downloadButton = document.getElementById('responses-download');

  if (!responsesList || !emptyState || !tableWrap) {
    return;
  }

  try {
    const response = await fetch(responsesApiUrl, {
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Could not load responses');
    }

    const responses = await response.json();
    responsesCache = Array.isArray(responses) ? responses : [];

    if (!Array.isArray(responses) || !responses.length) {
      emptyState.hidden = false;
      tableWrap.hidden = true;
      toggleResponsesDownloadButton(false);
      responsesList.innerHTML = '';
      emptyState.textContent = 'No responses have been saved yet. Submit feedback from the Feedback page to populate this list.';
      return;
    }

    emptyState.hidden = true;
    tableWrap.hidden = false;
    toggleResponsesDownloadButton(Boolean(downloadButton));
    responsesList.innerHTML = responses
      .map((responseItem) => {
        const submittedDate = formatResponseDate(responseItem.submittedAt);
        const safeName = escapeHtml(responseItem.name || 'Anonymous');
        const safeEmail = escapeHtml(responseItem.email || 'No email');
        const safeApp = escapeHtml(responseItem.app || 'Not specified');
        const safeType = escapeHtml(responseItem.feedbackType || 'General');
        const safeRating = escapeHtml(responseItem.rating || 'Not rated');
        const safeMessage = escapeHtml(responseItem.message || '');

        return `<tr><td data-label="Name">${safeName}</td><td data-label="Email">${safeEmail}</td><td data-label="App">${safeApp}</td><td data-label="Type">${safeType}</td><td data-label="Rating">${safeRating}</td><td data-label="Message" class="response-message-cell">${safeMessage}</td><td data-label="Submitted">${submittedDate}</td></tr>`;
      })
      .join('');
  } catch (error) {
    responsesCache = [];
    emptyState.hidden = false;
    tableWrap.hidden = true;
    toggleResponsesDownloadButton(false);
    responsesList.innerHTML = '';
    emptyState.textContent = 'Responses could not be loaded. Start the Python backend server to view saved feedback.';
  }
}

function formatResponseDate(value) {
  if (!value) {
    return 'Unknown date';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unknown date';
  }

  return date.toLocaleString();
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

renderResponses();

const responsesDownloadButton = document.getElementById('responses-download');
if (responsesDownloadButton) {
  responsesDownloadButton.addEventListener('click', downloadResponsesCsv);
}

function showFeedbackStatus(message, isError) {
  const successMessage = document.getElementById('success-msg');

  if (!successMessage) {
    return;
  }

  const heading = successMessage.querySelector('h3');
  const text = successMessage.querySelector('p');

  successMessage.classList.add('show');
  successMessage.classList.toggle('is-error', isError);

  if (heading) {
    heading.textContent = isError ? 'Feedback not sent' : 'Thank you for the feedback!';
  }

  if (text) {
    text.textContent = message;
  }
}

function initResponsesLoginPage() {
  const loginError = document.getElementById('responses-login-error');

  if (!loginError) {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  loginError.hidden = params.get('error') !== '1';
}

function toggleResponsesDownloadButton(isEnabled) {
  const downloadButton = document.getElementById('responses-download');

  if (!downloadButton) {
    return;
  }

  downloadButton.disabled = !isEnabled;
}

function downloadResponsesCsv() {
  if (!responsesCache.length) {
    return;
  }

  const headers = ['Name', 'Email', 'App', 'Type', 'Rating', 'Message', 'Submitted At'];
  const rows = responsesCache.map((item) => [
    item.name || '',
    item.email || '',
    item.app || '',
    item.feedbackType || '',
    item.rating || '',
    item.message || '',
    item.submittedAt || '',
  ]);
  const csvContent = [headers, ...rows]
    .map((row) => row.map(escapeCsvValue).join(','))
    .join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const fileUrl = URL.createObjectURL(blob);
  const downloadLink = document.createElement('a');
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');

  downloadLink.href = fileUrl;
  downloadLink.download = `focus-ai-responses-${timestamp}.csv`;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  document.body.removeChild(downloadLink);
  URL.revokeObjectURL(fileUrl);
}

function escapeCsvValue(value) {
  const escapedValue = String(value).replace(/"/g, '""');
  return `"${escapedValue}"`;
}