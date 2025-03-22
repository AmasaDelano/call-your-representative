var vue = require("vue/dist/vue.esm-bundler.js");
var repLookup = require("./data/rep_lookup");

(function () {
    
    async function lookupRepresentatives(address) {
        var response = await fetch("/lookup-reps.php?address=" + address).then(function (response) {
            var data = response.json();
            console.log(data);
            return data;
        });
        return response;
    }
    
    const app = vue.createApp({
        data: function () {
            return {
                address: "",
                addressInvalid: false,
                hasSearched: false,
                addressAccuracy: 1,
                state: "",
                congressionalDistrict: "",
                stateDistricts: [],
                reps: []
            };
        },
        mounted: function () {
            var districtsRaw = window.location.hash.substring(1);
            if (districtsRaw) {
                var districts = districtsRaw.split(",");
                this.state = districts[0];
                this.congressionalDistrict = districts[1];
                this.stateDistricts = (districts.length > 2 && districts.slice(2)) || [];

                this.loadReps(this.state, this.congressionalDistrict, this.stateDistricts);
            }
        },
        computed: {
            addressTooShort: function () {
                return this.address.length < 14;
            },
            currentUrl: function () {
                return window.location;
            }
        },
        methods: {
            searchWithAddress: async function () {
                if (this.addressTooShort) {
                    this.addressInvalid = true;
                    this.addressAccuracy = 1;
                    return;
                }
                this.addressInvalid = false;

                var response = await lookupRepresentatives(this.address);

                this.address = response.input.formatted_address;

                var repsFromApi = response.results[0];

                this.state = repsFromApi.address_components.state;
                this.congressionalDistrict = repsFromApi.fields.congressional_districts[0].district_number.toString();
                function mapStateLegislativeDistrict(district) {
                    return district.district_number;
                }
                var houseDistrict = repsFromApi.fields.state_legislative_districts.house.map(mapStateLegislativeDistrict)[0];
                var senateDistrict = repsFromApi.fields.state_legislative_districts.senate.map(mapStateLegislativeDistrict)[0];
                this.stateDistricts = [houseDistrict, senateDistrict];

                var veryAccurate = ["rooftop", "point", "interpolation", "range_interpolation", "nearest_rooftop_match"];
                // var prettyInaccurate = ["intersection", "street_center"];
                // var veryInaccurate = ["place", "county", "state"];
                var accuracy = repsFromApi.accuracy_type;
                if (veryAccurate.indexOf(accuracy) === -1) {
                    this.addressAccuracy = 0;
                    document.getElementById("address").scrollIntoView(true);
                    return;
                }
                this.addressAccuracy = 1;

                window.location.hash = "#" + [this.state, this.congressionalDistrict].concat(this.stateDistricts).join(",")

                this.loadReps(this.state, this.congressionalDistrict, this.stateDistricts);
            },
            loadReps: function (state, congressionalDistrict, stateDistricts) {
                var us_reps = (function () {
                    return Object.values(repLookup).filter(function (rep) {
                        if (rep.state === state && rep.rep_type === "sen" && !rep.is_state) {
                            return true;
                        }

                        if (rep.state === state && rep.rep_type === "rep" && (rep.district || "").toString() === congressionalDistrict && !rep.is_state) {
                            return true;
                        }

                        return false;
                    });
                }());
                
                var state_reps = (function () {
                    return Object.values(repLookup).filter(function (rep) {
                        return rep.state === state && stateDistricts.indexOf((rep.district || "").toString()) !== -1 && rep.is_state;
                    });
                }());
                
                this.reps = state_reps.concat(us_reps);
                console.log(this.reps);

                this.hasSearched = true;
                this.addressIsInvalid = false;
            },
            file: function (folder, name, ext) {
                return "./representatives/" + folder + "/" + name + "." + ext;
            },
            title: function (rep) {
                var genderTitle = "person";
                if (rep.gender === "F") {
                    genderTitle = "woman";
                } else if (rep.gender === "M") {
                    genderTitle = "man";
                } else if (rep.rep_type === "assembly") {
                    genderTitle = "member";
                }

                if (rep.rep_type === "sen") {
                    return "Senator";
                } else if (rep.rep_type === "rep" && !rep.is_state) {
                    return "Congress" + genderTitle;
                } else if (rep.rep_type === "delegate") {
                    return "Delegate";
                } else if (rep.rep_type === "assemly") {
                    return "Assembly" + genderTitle;
                } else {
                    return "Representative";
                }
            },
            location: function (rep) {
                if (rep.is_state) {
                    return rep.state + " " + this.title(rep) + " for District " + rep.district;
                } else {
                    if (rep.district === null) {
                        return "US Congress, State of " + rep.state;
                    }

                    return "US Congress, Congressional District " + rep.district + " of " + rep.state;
                }
            }
        }
    });

    app.mount("#app");
}());