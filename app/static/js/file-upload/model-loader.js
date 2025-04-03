/**
 * Model Loader for Upload page
 * Loads transcription models for the model selection dropdown
 */
document.addEventListener("DOMContentLoaded", function () {
  const modelDropdown = document.getElementById("transcription_model");
  const modelLoadingIndicator = document.getElementById(
    "modelLoadingIndicator",
  );
  const modelLocaleInput = document.getElementById("model_locale");
  const uploadForm = document.getElementById("uploadForm");

  if (!uploadForm) return;

  const modelsUrl = uploadForm.getAttribute("data-models-url");

  if (modelDropdown && modelsUrl) {
    if (modelLoadingIndicator) {
      modelLoadingIndicator.classList.remove("d-none");
    }

    window
      .fetchWithCsrf(modelsUrl)
      .then((response) => response.json())
      .then((data) => {
        while (modelDropdown.options.length > 1) {
          modelDropdown.remove(1);
        }

        if (data.models && data.models.length > 0) {
          data.models.forEach((model) => {
            const option = document.createElement("option");
            option.value = model.id;
            option.dataset.name = model.displayName; 
            option.dataset.locale = model.locale;
            option.textContent = model.displayName;
            modelDropdown.appendChild(option);
          });
        }
      })
      .catch((error) => {
        console.error("Error loading models:", error);
        const helpText = document.getElementById("modelHelp");
        if (helpText) {
          const errorEl = document.createElement("p");
          errorEl.className = "text-danger mt-1";
          errorEl.textContent = "Error loading transcription models.";
          helpText.parentNode.insertBefore(errorEl, helpText.nextSibling);
        }
      })
      .finally(() => {
        if (modelLoadingIndicator) {
          modelLoadingIndicator.classList.add("d-none");
        }
      });

    // Add event listener to update locale when model changes
    if (modelDropdown && modelLocaleInput) {
      modelDropdown.addEventListener("change", function () {
        const selectedOption =
          modelDropdown.options[modelDropdown.selectedIndex];
        if (
          selectedOption &&
          selectedOption.dataset &&
          selectedOption.dataset.locale
        ) {
          modelLocaleInput.value = selectedOption.dataset.locale;
        } else {
          modelLocaleInput.value = "";
        }
      });
    }
  }
});
