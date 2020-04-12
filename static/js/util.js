

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
    $('select').formSelect();
});


//Dropdown
$(document).ready(function () {
    $('.dropdown-trigger').dropdown();
});
//Sidenav

$(document).ready(function () {
    $('.sidenav').sidenav();
});

//Modal

$(document).ready(function () {
    $('.modal').modal();
});
//upload to AWS
(function() {
  document.getElementById("file_input").onchange = function(){
    var files = document.getElementById("file_input").files;
    var file = files[0];
    if(!file){
      return alert("No file selected.");
    }
    getSignedRequest(file);
  };
})();

function getSignedRequest(file){
  var xhr = new XMLHttpRequest();
  xhr.open("GET", file.name+"/"+file.type);

  xhr.onreadystatechange = function(){
      console.log(file.size)



        if(xhr.readyState === 4){
          if(xhr.status === 200){
            var response = JSON.parse(xhr.responseText);
            uploadFile(file, response.data, response.url);
          }
          else{
            alert("El archivo ha de ser una imagen");
          }
       }

      };
    if(file.size < 5000000){
      xhr.send();
    }else{
      alert("El archivo debe pesar menos de 5 mb");

    }
}


function uploadFile(file, s3Data, url){
  var xhr = new XMLHttpRequest();
  xhr.open("POST", s3Data.url);

  var postData = new FormData();
  for(key in s3Data.fields){
    postData.append(key, s3Data.fields[key]);
  }
  postData.append('file', file);
  xhr.onreadystatechange = function() {
    console.log(file.size);

    if(xhr.readyState === 4){
      if(xhr.status === 200 || xhr.status === 204){
        document.getElementById("preview").src = url;
        document.getElementById("avatar-url").value = url;
      }
      else{
        alert("No se ha podido subir el archivo");
      }
   }

  };
  xhr.send(postData);
}
