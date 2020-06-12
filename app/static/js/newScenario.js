$(document).ready(function() {
  $('[data-toggle="popover"]').popover();

    //Function to avoid showing error messages before input text
  $("#createButton").click(function(event) {
    var form = $("#newScenarioForm");
    if (form[0].checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    form.addClass('was-validated');
  });

  //Function to store form when page reloads
  $(function() {
    $("#newScenarioForm").sisyphus();
  });
});
