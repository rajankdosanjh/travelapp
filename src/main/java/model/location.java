public class location {
    private String name;
    private double latitude;
    private double longitude;
    private String description;
    private double tiktokReviewScore;

    public location(String name, double latitude, double longitude, String description, double tiktokReviewScore) {
        this.name = name;
        this.latitude = latitude;
        this.longitude = longitude;
        this.description = description;
        this.tiktokReviewScore = tiktokReviewScore;
    }

    //getters, ensure private fields in location class can be accessed
    public String getName() {
        return name;
    }

    public double getLatitude() {
        return latitude;
    }

    public double getLongitude() {
        return longitude;
    }

    public String getDescription() {
        return description;
    }

    public double getTiktokReviewScore() {
        return tiktokReviewScore;
    }

    //calculate distance method - calculates distances from one location to another
    public double calculateDistance(Location otherLocation) {
        final int EARTH_RADIUS_KM = 6371;

        double latDistance = Math.toRadians(otherLocation.getLatitude() - this.latitude);
        double lonDistance = Math.toRadians(otherLocation.getLongitude() - this.longitude);

        double a = Math.sin(latDistance / 2) * Math.sin(latDistance / 2)
                + Math.cos(Math.toRadians(this.latitude)) * Math.cos(Math.toRadians(otherLocation.getLatitude()))
                * Math.sin(lonDistance / 2) * Math.sin(lonDistance / 2);

        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return EARTH_RADIUS_KM * c;
    }
}
