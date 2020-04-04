
//Autocompletado

document.addEventListener('DOMContentLoaded', function() {
       var options = {
           data: {
               "HTML":null,
               "CSS":null,
           }
       }
    var elems = document.querySelectorAll('.autocomplete');
    var instances = M.Autocomplete.init(elems, options);
  });


//Geolocalizacion

 window.onload = getLocation();

    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(showPosition);
        } else {
            alert("Geolocation is not supported by this browser.");
        }
    }

    function showPosition(position) {
        let lat = position.coords.latitude;
        let long = position.coords.longitude;
        $("input[name='latitude']").val(lat);
        $("input[name='longitude']").val(long);
    }


//Select

 $(document).ready(function () {
      $('select').material_select();
    });


    document.addEventListener('DOMContentLoaded', function() {
    var elems = document.querySelectorAll('select');
    var instances = M.material_select.init(elems, options);
  });


//Dropdown

    $('.dropdown-trigger').dropdown();

//Sidenav No va

    $(document).ready(function () {
      $('.sidenav').sidenav();
    });


//Modal No va

  $(document).ready(function () {
      $('.modal').modal();
    });