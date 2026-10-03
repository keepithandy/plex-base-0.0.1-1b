function showMessage() {
  document.getElementById('status').textContent = 'Hello from Example.';
}

document.getElementById('action-button').addEventListener('click', showMessage);
