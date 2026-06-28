document.addEventListener("DOMContentLoaded", () => {

    const rutInput = document.getElementById("rut");

    if (!rutInput) return;

    rutInput.addEventListener("input", function () {

        let rut = this.value.toUpperCase();

        rut = rut.replace(/[^0-9K]/g, "");

        if (rut.length <= 1) {
            this.value = rut;
            return;
        }

        let cuerpo = rut.slice(0, -1);
        let dv = rut.slice(-1);

        cuerpo = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".");

        this.value = cuerpo + "-" + dv;

    });

});