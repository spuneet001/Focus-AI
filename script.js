let selectedRating = 0;

function selectRating(value) {
  selectedRating = value;
  document.querySelectorAll('.rating-btn').forEach((button, index) => {
    button.classList.toggle('selected', index < value);
  });
}

function submitFeedback(event) {
  event.preventDefault();

  const name = document.getElementById('fb-name');
  const email = document.getElementById('fb-email');
  const message = document.getElementById('fb-message');
  const app = document.getElementById('fb-app');
  const type = document.getElementById('fb-type');
  const successMessage = document.getElementById('success-msg');

  if (!name || !email || !message || !successMessage) {
    return;
  }

  if (!name.value.trim() || !email.value.trim() || !message.value.trim()) {
    window.alert('Please fill in your name, email, and message.');
    return;
  }

  successMessage.classList.add('show');
  name.value = '';
  email.value = '';
  message.value = '';

  if (app) app.value = '';
  if (type) type.value = '';

  selectedRating = 0;
  document.querySelectorAll('.rating-btn').forEach((button) => {
    button.classList.remove('selected');
  });

  window.setTimeout(() => {
    successMessage.classList.remove('show');
  }, 5000);
}