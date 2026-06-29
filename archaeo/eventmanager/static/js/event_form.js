(function () {
  const dormField = document.getElementById("id_dorm");
  const dormSubField = document.getElementById("id_dorm_sub");
  const dormGroups = window.rexDormGroups || {};

  if (!dormField || !dormSubField || !dormGroups) {
    return;
  }

  function setDormSubChoices(dormKey, preferredValue) {
    const options = dormGroups[dormKey] || [["N/A", "N/A"]];
    const selectedValue =
      preferredValue ||
      (options.some(([value]) => value === dormSubField.value)
        ? dormSubField.value
        : options[0][0]);

    dormSubField.innerHTML = "";
    options.forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      if (value === selectedValue) {
        option.selected = true;
      }
      dormSubField.appendChild(option);
    });
  }

  dormField.addEventListener("change", function () {
    setDormSubChoices(dormField.value);
  });

  setDormSubChoices(dormField.value, dormSubField.value);
})();
