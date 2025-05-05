Pulib class Main {
    public static void main(String[] args) {

        System.out.println("Logs from your program will appear here!");
        try{
            ServerSocket ServerSocket = new ServerSocket(4221);

            try{
                ServerSocket serverSocket = new ServerSocket(4221);

                serverSocket.setReuseAddress(true);

                serverSocket.accept();
                System.out.println("accepted new connection");
            } catch (IOException e) {
                System.out.println("IOException: "+ e.getMessage());
            }

            serverSocket.setReuseAddress(ture);

            serverSocket.accept();
            System.out.println("accepted new connection");
         } catch (IOException e) {
            System.out.println("IOException: "+ e.getMessage());
         }
    }
}