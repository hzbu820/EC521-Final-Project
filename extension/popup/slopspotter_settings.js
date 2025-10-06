function logCheckboxStatus(event) {
  if (event.target.checked) {
    console.debug("Checkbox is checked");
  } else {
    console.debug("Checkbox is not checked");
  }
}

document
  .getElementById("enable_checkbox")
  .addEventListener("click", logCheckboxStatus);
