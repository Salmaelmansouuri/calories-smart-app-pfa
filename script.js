const form = document.getElementById("predictionForm");
const resetBtn = document.getElementById("resetBtn");
const resultBox = document.getElementById("result");
const resultText = document.getElementById("resultText");

function setResultState(state, message) {
  resultBox.classList.remove("result-success", "result-error", "result-loading");

  if (state === "success") {
    resultBox.classList.add("result-success");
  } else if (state === "error") {
    resultBox.classList.add("result-error");
  } else if (state === "loading") {
    resultBox.classList.add("result-loading");
  }

  resultText.textContent = message;
}

form.addEventListener("submit", async function (e) {
  e.preventDefault();

  const data = {
    Gender: document.getElementById("Gender").value,
    Age: document.getElementById("Age").value,
    Height: document.getElementById("Height").value,
    Weight: document.getElementById("Weight").value,
    Duration: document.getElementById("Duration").value,
    Heart_Rate: document.getElementById("Heart_Rate").value,
    Body_Temp: document.getElementById("Body_Temp").value
  };

  setResultState("loading", "Predicting...");

  try {
    const response = await fetch("http://172.20.10.3:5000/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.predicted_calories !== undefined) {
      setResultState("success", `Predicted Calories Burnt: ${result.predicted_calories}`);
    } else {
      setResultState("error", `Error: ${result.error}`);
    }
  } catch (error) {
    setResultState("error", "Could not connect to the backend.");
  }
});

resetBtn.addEventListener("click", function () {
  form.reset();
  resultBox.classList.remove("result-success", "result-error", "result-loading");
  resultText.textContent = "No prediction yet.";
});