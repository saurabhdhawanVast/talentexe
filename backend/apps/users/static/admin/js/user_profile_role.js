(function () {
  'use strict';

  function toggleEmployeeSection(role) {
    var section = document.querySelector('.employee-only-section');
    if (!section) return;
    section.style.display = (role === 'employee') ? '' : 'none';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var roleSelect = document.getElementById('id_role');
    if (!roleSelect) return;

    // Initial state
    toggleEmployeeSection(roleSelect.value);

    roleSelect.addEventListener('change', function () {
      toggleEmployeeSection(this.value);
    });
  });
})();
