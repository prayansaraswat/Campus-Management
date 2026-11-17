// Client-side interactions for Campus Concern Portal

document.addEventListener("DOMContentLoaded", function () {
  // Category change listener on Concern submission form
  const categorySelect = document.getElementById("category");
  const maintenanceAlert = document.getElementById("maintenance-external-alert");
  const submitBtn = document.getElementById("submit-concern-btn");

  if (categorySelect && maintenanceAlert) {
    function checkCategory() {
      const selectedValue = categorySelect.value;
      if (
        selectedValue === "Maintenance/Housekeeping" ||
        selectedValue.toLowerCase().includes("maintenance")
      ) {
        maintenanceAlert.classList.remove("d-none");
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add("disabled");
        }
      } else {
        maintenanceAlert.classList.add("d-none");
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.classList.remove("disabled");
        }
      }
    }

    categorySelect.addEventListener("change", checkCategory);
    checkCategory(); // Initial check on page load
  }

  // Appointment status change dynamic display
  const appointmentActionSelect = document.getElementById("action");
  const rescheduleFields = document.getElementById("reschedule-fields-container");

  if (appointmentActionSelect && rescheduleFields) {
    function toggleRescheduleFields() {
      if (appointmentActionSelect.value === "Rescheduled") {
        rescheduleFields.classList.remove("d-none");
      } else {
        rescheduleFields.classList.add("d-none");
      }
    }

    appointmentActionSelect.addEventListener("change", toggleRescheduleFields);
    toggleRescheduleFields();
  }
});
