# This file compares two curves

def HasMetrics(line):
  if line[0:1] != "B":
    return True
  return False

def DataBetter(baseline_sorted, other_sorted):
  """
  Compares two data sets and determines which is better and by how
  much. Also produces a histogram of how much better, by PSNR.
  """

  def GraphBetter(metric_set1_sorted, metric_set2_sorted, base_is_set_2):
    """
    Search through the sorted metric file for metrics on either side of
    the metric from file 1.  Since both lists are sorted we really
    should not have to search through the entire range, but these
    are small files."""
    total_bitrate_difference_ratio = 0.0
    count = 0
    for data_pair in metric_set1_sorted:
      bitrate = data_pair[0]
      metric = data_pair[1]
      for i in range(len(metric_set2_sorted) - 1):
        #s2_bitrate_0, s2_metric_0 = metric_set2_sorted[i]
        #s2_bitrate_1, s2_metric_1 = metric_set2_sorted[i + 1]
        pair0 = metric_set2_sorted[i]
        s2_bitrate_0 = pair0[0]
        s2_metric_0 = pair0[1]

        pair1 = metric_set2_sorted[i + 1]
        s2_bitrate_1 = pair1[0]
        s2_metric_1 = pair1[1]

        # We have a point on either side of our metric range.
        if metric >= s2_metric_0 and metric <= s2_metric_1:

          # Calculate a slope.
          if s2_metric_1 - s2_metric_0 != 0:
            metric_slope = ((s2_bitrate_1 - s2_bitrate_0) /
                            (s2_metric_1 - s2_metric_0))
          else:
            metric_slope = 0

          estimated_s2_bitrate = (s2_bitrate_0 + (metric - s2_metric_0) *
                                  metric_slope)

          # Calculate percentage difference as given by base.
          if base_is_set_2 == 0:
            bitrate_difference_ratio = ((bitrate - estimated_s2_bitrate) /
                                        bitrate)
          else:
            bitrate_difference_ratio = ((bitrate - estimated_s2_bitrate) /
                                        estimated_s2_bitrate)

          total_bitrate_difference_ratio += bitrate_difference_ratio
          count += 1
          break


    # Calculate the average improvement between graphs.
    if count != 0:
      avg = total_bitrate_difference_ratio / count

    else:
      avg = 0.0

    return avg

  # If one of the curves is not specified
  if baseline_sorted is None or other_sorted is None:
    return None

  # Be fair to both graphs by testing all the points in each.
  avg_improvement = (GraphBetter(baseline_sorted, other_sorted, 0) -
                     GraphBetter(other_sorted, baseline_sorted, 1)) / 2


  return avg_improvement
