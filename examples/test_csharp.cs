// Test C# file with intentional violations
using System;
using System.Threading.Tasks;

public class badClassName
{
    public async Task DoSomethingAsync()
    {
        // Async method without await
        Console.WriteLine("No await here");
    }

    public async Task GoodAsyncMethod()
    {
        await Task.Delay(100);
    }

    public string GetNull()
    {
        return null;  // Returning null
    }

    public void badMethodName()
    {
        // Method name not PascalCase
        Console.WriteLine("Bad naming");
    }

    public void GoodMethodName()
    {
        Console.WriteLine("Good naming");
    }
}

public class GoodClassName
{
    public void AnotherMethod()
    {
        Console.WriteLine("OK");
    }
}
