def d_grade_processor(data):
    """
    D Grade Code - High Energy Cost (Score: 40-54)
    
    This code contains significant inefficiencies:
    - Double nested loops
    - Multiple allocations in loops
    - Expensive operations (sorting) in loops
    - Unnecessary computations
    """
    results = []
    
    # Double nested loop
    for i in range(len(data)):
        row_result = []
        
        # First inner loop with multiple operations
        temp_storage = []
        for j in range(len(data[i])):
            # List allocation in inner loop
            temp = [data[i][j] * k for k in range(8)]
            
            # Expensive operation: sorting in loop
            sorted_temp = sorted(temp)
            
            # Dictionary allocation
            item_dict = {
                'original': data[i][j],
                'squared': data[i][j] ** 2,
                'cubed': data[i][j] ** 3,
                'processed': sorted_temp
            }
            
            temp_storage.append(item_dict)
            row_result.append(sum(temp))
        
        # Second inner loop (another pass over same data - inefficient!)
        averages = []
        for item_dict in temp_storage:
            avg = sum([item_dict['squared'], item_dict['cubed']]) / 2
            averages.append(avg)
        
        # More allocations in outer loop
        results.append({
            'row_index': i,
            'data': row_result,
            'averages': averages,
            'row_sum': sum(row_result),
            'row_avg': sum(row_result) / len(row_result) if row_result else 0
        })
    
    return results

# Test with sample data
test_data = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]
result = d_grade_processor(test_data)

# Print summary
for i, item in enumerate(result[:2]):  # Show first 2 rows
    print(f"Row {i}: sum={item['row_sum']:.2f}, avg={item['row_avg']:.2f}")