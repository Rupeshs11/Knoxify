/**
 * Knoxify - Handles file upload, status polling, and audio playback
 */

const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const voiceSelect = document.getElementById("voiceSelect");
const convertBtn = document.getElementById("convertBtn");
const btnText = convertBtn.querySelector(".btn-text");
const btnLoader = convertBtn.querySelector(".btn-loader");
const statusSection = document.getElementById("statusSection");
const statusText = document.getElementById("statusText");
const statusDot = statusSection.querySelector(".status-dot");
const errorSection = document.getElementById("errorSection");
const errorText = document.getElementById("errorText");
const audioSection = document.getElementById("audioSection");
const audioPlayer = document.getElementById("audioPlayer");
const downloadBtn = document.getElementById("downloadBtn");

let currentJobId = null;
let pollInterval = null;

function init() {
  fileInput.addEventListener("change", handleFileSelect);
  uploadForm.addEventListener("submit", handleFormSubmit);
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  const wrapper = fileInput.closest(".file-input-wrapper");

  if (file) {
    if (!file.name.endsWith(".txt")) {
      showError("Please select a .txt file");
      fileInput.value = "";
      wrapper.classList.remove("has-file");
      fileName.textContent = "Choose a .txt file";
      return;
    }

    if (file.size > 50 * 1024) {
      showError("File size exceeds 50 KB limit");
      fileInput.value = "";
      wrapper.classList.remove("has-file");
      fileName.textContent = "Choose a .txt file";
      return;
    }

    wrapper.classList.add("has-file");
    fileName.textContent = file.name;
    hideError();
  } else {
    wrapper.classList.remove("has-file");
    fileName.textContent = "Choose a .txt file";
  }
}

async function handleFormSubmit(event) {
  event.preventDefault();

  const file = fileInput.files[0];
  if (!file) {
    showError("Please select a file");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("voice", voiceSelect.value);

  hideError();
  hideAudioSection();
  hideStatus();
  setProcessingState(true);
  showStatus("Uploading file...", "uploading");

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Upload failed");
    }

    currentJobId = data.job_id;
    showStatus("Processing audio...", "processing");
    startPolling();
  } catch (error) {
    showError(error.message);
    setProcessingState(false);
    hideStatus();
  }
}

function startPolling() {
  pollInterval = setInterval(checkStatus, 1000);
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

async function checkStatus() {
  if (!currentJobId) {
    stopPolling();
    return;
  }

  try {
    const response = await fetch(`/status/${currentJobId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Status check failed");
    }

    switch (data.status) {
      case "processing":
        showStatus("Processing audio...", "processing");
        break;

      case "ready":
        stopPolling();
        showStatus("Audio ready!", "ready");
        showAudioSection(data.download_url);
        setProcessingState(false);
        break;

      case "error":
        stopPolling();
        showError(data.error || "Processing failed");
        hideStatus();
        setProcessingState(false);
        break;
    }
  } catch (error) {
    stopPolling();
    showError(error.message);
    hideStatus();
    setProcessingState(false);
  }
}

function setProcessingState(isProcessing) {
  convertBtn.disabled = isProcessing;
  fileInput.disabled = isProcessing;
  voiceSelect.disabled = isProcessing;

  if (isProcessing) {
    btnText.hidden = true;
    btnLoader.hidden = false;
  } else {
    btnText.hidden = false;
    btnLoader.hidden = true;
  }
}

function showStatus(message, state) {
  statusSection.hidden = false;
  statusText.textContent = message;
  statusDot.className = "status-dot";
  if (state) {
    statusDot.classList.add(state);
  }
}

function hideStatus() {
  statusSection.hidden = true;
  statusText.textContent = "";
  statusDot.className = "status-dot";
}

function showError(message) {
  errorSection.hidden = false;
  errorText.textContent = message;
}

function hideError() {
  errorSection.hidden = true;
  errorText.textContent = "";
}

function showAudioSection(downloadUrl) {
  audioSection.hidden = false;
  if (downloadUrl) {
    audioPlayer.src = downloadUrl;
    downloadBtn.href = downloadUrl;
  } else {
    audioPlayer.removeAttribute("src");
    downloadBtn.href = "#";
  }
}

function hideAudioSection() {
  audioSection.hidden = true;
  audioPlayer.src = "";
}

function resetForm() {
  uploadForm.reset();
  fileName.textContent = "Choose a .txt file";
  fileInput.closest(".file-input-wrapper").classList.remove("has-file");
  hideError();
  hideStatus();
  hideAudioSection();
  currentJobId = null;
}

document.addEventListener("DOMContentLoaded", init);
