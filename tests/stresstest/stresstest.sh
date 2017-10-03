
curl -F "filecomment=This is an image file" -F "image=@/home/playground/dog1.jpg" https://playground.imagemonkey.io/v1/predict &

pidlist="$pidlist $!" 

for job in $pidlist do
  echo $job     
  wait $job || let "FAIL+=1" 
done  

if [ "$FAIL" == "0" ]; then 
  echo "YAY!" 
else 
  echo "FAIL! ($FAIL)" 
fi
