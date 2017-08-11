var width = 1000,
    height = 500,
    radius = 6;

var attached_text, text_on;
var commTypeChecked = new Array(true, true, true); // by default, all communication types are checked

var node_opacity_val = 0.8;
var link_opacity_val = 0.8;
var node, link, fnode, linkData, nodeData, force, max_weight = 0, max_weight_node = null;
var linkedByIndex = {};					
var lastSelNode = null, lastSelLink = null, lastSelLinkClr = null, lastSelNodeName = null, lastSelEdgeSource=-1, lastSelEdgeTarget=-1;
var node_stroke_clr = d3.rgb(142, 186, 229).darker();
var node_fill_clr = d3.rgb(153, 186, 221);
var link_sel_clr;
var zoom = d3.behavior.zoom();

d3.select("#datainfo").style.width=width+"px";	

var svg = d3.select("#chart").append("svg")
        .attr("width", width)
        .attr("height", height)
	    .append("g")
		.call(zoom.scaleExtent([1, 4]).on("zoom", zoom_redraw));

// this rect is important to have zoom and pan work
var rect = svg.append("rect")
    .attr("width", width)
    .attr("height", height)
    .style("fill", "none")
    .style("pointer-events", "all");

force = d3.layout.force()
          .gravity(.1)
          .charge(-200)
          .linkDistance(100)
          .size([width, height]);

function zoom_redraw() {
	 svg.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
    //svg.attr("transform", "scale(" + d3.event.scale + ")");
}

function tick() {
	node.attr("transform", function(d) {
		d.x = Math.max(radius, Math.min(width - radius, d.x));
		d.y = Math.max(radius, Math.min(height - radius, d.y));
    	return "translate(" + d.x + "," + d.y + ")";
    });

	//link.attr("x1", function(d) { return d.source.x; })
    //	.attr("y1", function(d) { return d.source.y; })
    //	.attr("x2", function(d) { return d.target.x; })
    //	.attr("y2", function(d) { return d.target.y; });
    link.attr("d", function(d) {
        var dx = d.target.x - d.source.x,
            dy = d.target.y - d.source.y,
            //dr = Math.sqrt(dx*dx+dy*dy);
            dr = 150/d.linknum;
        return "M" + d.source.x + "," + d.source.y + "A" + dr + "," + dr + " 0 0,1 " + d.target.x + "," + d.target.y;
    })
}

var node_drag = d3.behavior.drag()
    .on("dragstart", dragstart)
    .on("drag", dragmove)
    .on("dragend", dragend);
    
function dragstart(d, i) {
	d3.event.sourceEvent.stopPropagation(); // very important; otherwise, panning will interfare with node dragging
    force.stop() // stops the force auto positioning before you start dragging
}

function dragmove(d, i) {
    d.px += d3.event.dx;
    d.py += d3.event.dy;
    d.x += d3.event.dx;
    d.y += d3.event.dy;
    tick(); // this is the key to make it work together with updating both px,py,x,y on d !
}

function dragend(d, i) {
    d.fixed = true; // set the node to fixed so the force doesn't include the node in its auto positioning stuff
    tick();
    force.resume();
}

function isConnected(a, b) {
    return linkedByIndex[a.index + "," + b.index] || linkedByIndex[b.index + "," + a.index] || a.index == b.index;
}

function fadeRelativeToNode(opacity) {
	return function(d) {
        fnode.style("opacity", function(o) {
	    	var thisOpacity = isConnected(d, o) ? node_opacity_val : opacity;
            if (opacity < node_opacity_val && thisOpacity == node_opacity_val) {
                d3.select(this).select("text").transition()
                    .duration(200)
                    .style("visibility", "visible");
            }
            else if (opacity < node_opacity_val) {
                d3.select(this).select("text").transition()
                    .duration(200)
                    .style("visibility", "hidden");
            }
            return thisOpacity;
	  	});

	  	link.style("stroke-opacity", function(o) {
	      	return o.source.index == d.index || o.target.index == d.index ? link_opacity_val : (opacity < node_opacity_val ? opacity : link_opacity_val);
	  	});

		if(opacity == node_opacity_val) {
		    if (text_on)
                attached_text.style("visibility", "visible");
            else
                attached_text.style("visibility", "hidden");
		}
	}
}

function fadeRelativeToLink(opacity) {
    return function(d) {
        if (typeof(fnode) != "undefined")
            fnode.style("opacity", function(o) {
                thisOpacity = (o.index==d.source.index || o.index==d.target.index ? node_opacity_val : opacity);
                if (opacity < link_opacity_val && thisOpacity == node_opacity_val) {
                    d3.select(this).select("text").transition()
                        .duration(200)
                        .style("visibility", "visible");
                }
                else if (opacity == link_opacity_val) {
                    // mouse out
                    d3.select(this).select("text").transition()
                        .duration(200)
                        .style("visibility", text_on ? "visible" : "hidden");
                }
                return thisOpacity;
            });

        link.style("stroke-opacity", function(o) {
            if (o.source.index == d.source.index && o.target.index == d.target.index)
                return link_opacity_val;
            else
                return opacity;
        });
    }
}

function get_node_size(weight, msg_cnt) {
    if (weight > 0)
        return 2+Math.sqrt(weight*radius)-0.75;
    else
        return 2+Math.sqrt(msg_cnt*radius)-0.75;
}

function updateData() {
	force
		.nodes(nodeData)
	    .links(linkData)
		.start(); // has to be call here to make weight property on node available

    link = svg.selectAll("path.link")
        .data(force.links())
        .enter().append("path")

    link.attr("class", function(d) { return "link " + d.type; })
		.style("stroke-opacity", link_opacity_val)
	    //.style("stroke-width", function(d) { return 1 + Math.sqrt(d.count); })
        .style("stroke-width", 1)
	    .on("mouseover", fadeRelativeToLink(0.1))
        .on("mouseout", fadeRelativeToLink(link_opacity_val))
		.on("click", function(d) {
			selEdgeSource = d.source;
			selEdgeTarget = d.target;
			var sel_same_link = false;
	        if (lastSelEdgeSource == selEdgeSource && lastSelEdgeTarget == selEdgeTarget)
	        	sel_same_link = true;

			// clear out previously clicked/hgted other links if any
			if(lastSelLink != null) {
				lastSelLink.style("stroke", lastSelLinkClr);
				lastSelEdgeSource = -1;
				lastSelEdgeTarget = -1;
			}
			// clear out previously clicked/hgted node if any
			if(lastSelNode != null) {
	            lastSelNode.style("stroke", node_stroke_clr);
	            lastSelNodeName = null;
	            lastSelNode = null;
	        }

			if(!sel_same_link) {
				lastSelLink = d3.select(this);
                lastSelLinkClr = lastSelLink.style('stroke')
				lastSelLink.transition()
					.duration(500)
					.style("stroke", "black");
				htmltext = "<b>Slack Communication Channels</b>: " + d.channel + "<br>";

                if (d.type == 'at') {
                    htmltext = "<b>Communication Type</b>: @-mention<br>";
                    htmltext += "<b>Message initiator: </b>: " + d.source.name + "<br>";
                    htmltext += "<b>User being @-mentioned: </b>: " + d.target.name + "<br>";
                    htmltext += "<b>Message:</b> " + d.text + "<br>";
                }
                else {
                    htmltext = "<b>Communication Type</b>: " + d.type + "<br>";
                    htmltext += "<b>Message initiator: </b>: " + d.source.name + "<br>";
                    htmltext += "<b>Message reactor: </b>: " + d.target.name + "<br>";
                    htmltext += "<b>Parent Message:</b> " + d.text + "<br>";
                }

                if (d.threaded_text)
                    htmltext += "<b>Threaded Messages:</b> " + d.threaded_text + "<br>";
                if (d.reactions)
                    htmltext += "<b>Reactions:</b> " + d.reactions + "<br>";
				d3.select("#datainfo").html(htmltext);
				lastSelEdgeSource = selEdgeSource;
				lastSelEdgeTarget = selEdgeTarget;
			}
			else {// clear out the selection if the selected link is clicked again
				d3.select(this).transition()
					.duration(500)
					.style("stroke", lastSelLinkClr);
				lastSelLink = null;
                lastSelLinkClr = null;
				lastSelEdgeSource = -1;
				lastSelEdgeTarget = -1;
				d3.select("#datainfo").html("");
			}

			// clear out previously clicked/hgted other nodes if any
			if(lastSelNode != null) {
				lastSelNode.style("stroke", node_stroke_clr);
				lastSelNode = null;
			}
		});
    /*
    var filterLink = false;
    for(var index=0; index < commTypeChecked.length; index++)
        if (!commTypeChecked[index]) {
            filterLink = true;
            break;
        }
	if (filterLink) {
        flink = glink.filter(function (d) {
            if (commTypeChecked[0]) {// mention is checked
                if (d.type == 'at') {
                    return true;
                }
            }
            else if (commTypeChecked[1]) {// thread is checked
                if (d.type == 'thread') {
                    return true;
                }
            }
            else if (commTypeChecked[2]) {// reaction is checked
                if (d.type == 'reaction') {
                    return true;
                }
            }
            return false;
        });
    }
    else {
        flink = glink.filter(function (d) { return true; });
    }
    */

    var node_drag = d3.behavior.drag()
        .on("dragstart", dragstart)
        .on("drag", dragmove)
        .on("dragend", dragend);
        	    
	node = svg.selectAll(".node")
	    .data(force.nodes());
	
	node.enter().append("g")
	    .attr("class", "node")     
	    .on("click", function(d) {
	        // clear out previously clicked/hgted link if any
	        if(lastSelLink != null) {
	            lastSelLink.style("stroke", "#999");
	            lastSelLink = null;
	            lastSelEdgeSource = -1;
				lastSelEdgeTarget = -1;
	        }
	        var sel_same_node = false;
	        if (lastSelNodeName == d.name)
	        	sel_same_node = true;
	        
	        if(lastSelNode != null) {
	            lastSelNode.transition() 
	                .duration(500)
	                .style("stroke", node_stroke_clr)
	            d3.select("#datainfo").html(""); 
                lastSelNode = null;	
                lastSelNodeName = null;				
	        }
	        
	        if(!sel_same_node) {		        
	            htmltext = "<b>" + d.name +"  </b>" + d.email + "<br><br>";
                if (d.broadcast_msg_count > 0)
                    htmltext += "<b>Number of broadcast messages:</b> " + d.broadcast_msg_count + "<br>";
                    if (d.broadcast_msg_count > 5)
                        htmltext += "<b>Top 5 broadcast messages:</b> " + d.broadcast_messages + "<br>";
                    else
                        htmltext += "<b>Broadcast messages:</b> " + d.broadcast_messages + "<br>";

	            d3.select("#datainfo").html(htmltext); 
		        lastSelNode = d3.select(this).select("circle");
		        lastSelNodeName = d.name; 
		        lastSelNode.transition() 
		            .duration(500)
		            .style("stroke", "#000000");
		    }
	    })       
		.call(force.drag)
		.on("mouseover", fadeRelativeToNode(0.1))
		.on("mouseout", fadeRelativeToNode(node_opacity_val))
		.call(node_drag);

    fnode = node.filter(function(d) {
        if(d.weight > max_weight) {
            max_weight = d.weight;
            max_weight_node = d;
        }
        return d.broadcast_msg_count > 0 || d.weight > 0;
	});
    if (max_weight_node != null) {
        max_weight_node.px = width/2;
        max_weight_node.py = height/2;
        max_weight_node.fixed = true;
    }

    fnode.append("circle")/
		.attr("r",
            function(d) {
                return get_node_size(d.weight, d.broadcast_msg_count);
		})
        .style("fill", function(d) { return d.color; })
		.style("opacity", node_opacity_val)
		.style("stroke", node_stroke_clr);

	attached_text = fnode.append("text")
    	.attr("dx", function(d) { return get_node_size(d.weight, d.broadcast_msg_count) + 2; })
    	.attr("dy", ".35em")
    	.text(function(d) { return d.name; })
        .style("visibility", "hidden");
    text_on = false;
    linkedByIndex = {};
    link.data().forEach(function(d) {
        linkedByIndex[d.source.index + "," + d.target.index] = 1;
    });

	force.on("tick", tick);
}

function filterGraph(aType, aVisibility) {
    link.style("visibility", function (o) {
        var lOriVisibility = d3.select(this).style("visibility");
        return (o.type == aType) ? aVisibility : lOriVisibility;
    });
}

// handle medium checkbox click events
function handleClick_mention(cb) {
	if(commTypeChecked[0] == cb.checked) return;
	commTypeChecked[0] = cb.checked;
	filterGraph("at", cb.checked ? "visible" : "hidden");
}

function handleClick_thread(cb) {
	if(commTypeChecked[1] == cb.checked) return;
	commTypeChecked[1] = cb.checked;
	filterGraph("thread", cb.checked ? "visible" : "hidden");
}

function handleClick_reaction(cb) {
	if(commTypeChecked[2] == cb.checked) return;
	commTypeChecked[2] = cb.checked;
	filterGraph("reaction", cb.checked ? "visible" : "hidden");
}

function ResetView() {
	zoom.scale(1);
	zoom.translate([0, 0]);
	svg.attr("transform", "translate(" + zoom.translate() + ")scale(" + zoom.scale() + ")");
}

function ToggleTextDisplay(cb) {
    text_on = cb.checked;
    if (cb.checked) {
        attached_text.style("visibility", "visible");
    }
    else {
        attached_text.style("visibility", "hidden");
    }
}

d3.json("inputData.json", function(json) {
	nodeData = json.nodes;
    linkData = json.links;
    // sort linkData so that "linknum" can be computed for each link for arc computation
    // for each pair of link connecting to the same source and target nodes
    linkData.sort(function(a, b) {
        if(a.source > b.source)
            return 1;
        else if (a.source < b.source)
            return -1;
        else {
            if(a.target > b.target)
                return 1;
            else if (a.target < b.target)
                return -1;
            else
                return 0;
        }
    });

    // any links with duplicate source and target get an incremented 'linknum' for arc radius computation
    if (linkData.length > 0) {
        linkData[0].linknum = 1;
        for (var i=1; i<linkData.length; i++) {
            if ((linkData[i].source == linkData[i-1].source && linkData[i].target == linkData[i-1].target)
                || (linkData[i].target == linkData[i-1].source && linkData[i].source == linkData[i-1].target)) {
                linkData[i].linknum = linkData[i - 1].linknum + 1;
                // console.log("source=" + linkData[i].source + ", target=" + linkData[i].target + ", linknum=" + linkData[i].linknum);
            }
            else
                linkData[i].linknum = 1;
        }
    }

	updateData();
});
