var color = d3.scale.linear()
	//.domain([10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70])
	//.range(["#ddd", "#ccc", "#bbb", "#aaa", "#999", "#888", "#777", "#666", "#555", "#444", "#333", "#222"]);
	.domain([0,1])
    .range(["#fff", "#111"]);

//var fill = d3.scale.category20();
var width = 780, height = 480;
	
var frequency_list;

function scale_size(s) {
	return 5 + s*60;
}

var c_svg = d3.select("#keyword_chart").append("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("class", "wordcloud");

function load_cloud_data(filename) {
    c_svg.selectAll('g').remove();
    d3.json(filename, function (data) {
        frequency_list = data.words;
        d3.layout.cloud().size([width, height])
            .words(frequency_list)
            .padding(5)
            .rotate(0)
            .fontSize(function (d) {
                return scale_size(d.size);
            })
            .on("end", draw)
            .start();
    });
}
	
function draw(words) {
    // without the transform, words would get cutoff to the left and top, they would
    // appear outside of the SVG area
	c_svg.append("g")
        .attr("transform", "translate(" + width/2 + "," + height/2 + ")")
		.selectAll("text")
		.data(frequency_list)
		.enter().append("text")
		.style("font-size", function(d) { return d.size + "px"; })
		.attr('text-anchor', 'middle')
		.style("fill", function(d, i) { return  color(d.size); }) // fill(i); })
		.attr("transform", function(d) {
			return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
		})
		.text(function(d) { return d.text; });
}
