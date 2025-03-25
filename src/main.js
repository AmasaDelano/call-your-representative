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
                stateHouseDistrict: "",
                stateSenateDistrict: "",
                reps: []
            };
        },
        mounted: function () {
            this.loadRepsFromHash();

            var that = this;
            window.addEventListener("hashchange", function () {
                that.loadRepsFromHash();
            });
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

                if (response.error) {
                    this.addressInvalid = true;
                    this.addressAccuracy = 0;
                    return;
                }
                
                var repsFromApi = response.results[0];

                this.address = repsFromApi.formatted_address;
                
                this.state = repsFromApi.address_components.state;
                this.congressionalDistrict = repsFromApi.fields.congressional_districts[0].district_number.toString();
                function mapStateLegislativeDistrict(district) {
                    return district.district_number;
                }
                this.stateHouseDistrict = repsFromApi.fields.state_legislative_districts.house.map(mapStateLegislativeDistrict)[0];
                this.stateSenateDistrict = repsFromApi.fields.state_legislative_districts.senate.map(mapStateLegislativeDistrict)[0];

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

                window.location.hash = "#" + [this.state, this.congressionalDistrict, this.stateHouseDistrict, this.stateSenateDistrict].join(",")

                this.loadReps(this.state, this.congressionalDistrict, this.stateHouseDistrict, this.stateSenateDistrict);
            },
            loadRepsFromHash: function () {
                var districtsRaw = window.location.hash.substring(1);
                if (districtsRaw) {
                    var districts = districtsRaw.split(",");
                    this.state = districts[0];
                    this.congressionalDistrict = districts[1];
                    this.stateHouseDistrict = districts[2];
                    this.stateSenateDistrict = districts[3];
    
                    this.loadReps(this.state, this.congressionalDistrict, this.stateHouseDistrict, this.stateSenateDistrict);
                } else {
                    this.hasSearched = false;
                    this.addressInvalid = false;
                    this.addressAccuracy = 1;
                }
            },
            loadReps: function (state, congressionalDistrict, stateHouseDistrict, stateSenateDistrict) {
                function toString(text) {
                    return (text || "").toString();
                }
                var us_reps = (function () {
                    return Object.values(repLookup).filter(function (rep) {
                        if (rep.is_state || rep.state !== state) {
                            return false;
                        }

                        if (rep.rep_type === "sen") {
                            return true;
                        }

                        if (toString(rep.district) === congressionalDistrict) {
                            return true;
                        }

                        return false;
                    });
                }());
                
                var state_reps = (function () {
                    return Object.values(repLookup).filter(function (rep) {
                        if (!rep.is_state || rep.state !== state) {
                            return false;
                        }
                        
                        if (rep.rep_type === "sen" && stateSenateDistrict === toString(rep.district)) {
                            return true;
                        }

                        if (rep.rep_type !== "sen" && stateHouseDistrict === toString(rep.district)) {
                            return true;
                        }
                        
                        return false;
                    });
                }());
                
                this.reps = state_reps.concat(us_reps);
                this.reps.sort(function (a, b) {
                    if (a.is_state && !b.is_state) {
                        return -1; // a first
                    }

                    if (!a.is_state && b.is_state) {
                        return 1; // b first
                    }

                    if (a.rep_type === "sen" && b.rep_type !== "sen") {
                        return 1; // b first
                    }

                    if (a.rep_type !== "sen" && b.rep_type === "sen") {
                        return -1; // a first
                    }

                    return 0;
                });
                console.log(this.reps);

                this.hasSearched = true;
                this.addressInvalid = false;
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
                } else if (rep.rep_type === "assembly") {
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
            },
            contact_contents: function (rep) {
                parts = []
                if (rep.phone_found) {
                    parts.push("phone number");
                }
                if (rep.phone_found) {
                    parts.push("email address");
                } else if (rep.phone_found) {
                    parts.push("submission form");
                }

                if (parts.length === 1) {
                    return parts[0];
                }
                if (parts.length === 2) {
                    return parts[0] + " and " + parts[1];
                }
                if (parts.length === 3) {
                    return parts[0] + ", " + parts[1] + ", and " + parts[2];
                }
            },
            obj_pronoun: function (rep) {
                if (rep.gender === "F") {
                    return "her";
                }
                if (rep.gender === "M") {
                    return "him";
                }
                return "them";
            },
            poss_pronoun: function (rep) {
                if (rep.gender === "F") {
                    return "her";
                }
                if (rep.gender === "M") {
                    return "his";
                }
                return "their";
            }
        }
    });

    app.mount("#app");
}());