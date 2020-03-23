function comission() {
    var price = document.getElementsByName("price")[0];
    var comission = "0%";

    if (price > 0 & price < 0.5) {
      comission = "10cents";
    } else if (price > 0.5 & price < 1.5) {
      comission = "15%";
    } else if (price > 1.5 & price < 3) {
      comission = "20%";
    } else if (price > 3 & price < 5) {
      comission = "25%";
    } else {
      comission = "27%";
    }
    document.body.innerHTML = "<h4>Se cobrará un " + comission + " de cada transacción a modo de gastos de mantenimiento de la aplicación.</h4>" ;
  }