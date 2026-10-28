difference() {
    cylinder(5,9.1,9.1);
    translate([0,0,1]) cylinder(8,8.1,8.1);
    translate([0,0,3]) rotate([0,90,0]) cylinder(12,1,1);
    translate([7.7,-.85,3]) cube([1.75,1.75,8]);
}    

h=3.8;
translate([0,-8,h/2]) scale([2,2,h]) cube(1,1,1, center=true);
translate([0,8,h/2]) scale([2,2,h]) cube(1,1,1, center=true);
translate([-8,0,h/2]) scale([2,2,h]) cube(1,1,1, center=true);