/*$(function()
{

  $("#searchbar").keyup(function() 
  {
    // Declare variables
    var filter;
    filter = $(this).val().toUpperCase();

    $(".article_post").each(function(i, obj) 
    {
  
      if ($("a",this).text().toUpperCase().indexOf(filter) > -1 )
      {
        $(this).css("display","");
      }else{
        $(this).css("display","none");
      }
    });
  });
});
*/